"""Every URL a claim cites must have actually been returned by Parallel.

A model asked to "preserve citations" will sometimes produce a citation that
looks correct and was never retrieved. Instructions cannot prevent that; only
checking can. So the Parallel tools record what they really returned, and the
evidence builder refuses any source that is not in that record.

The registry is per investigation and lives only for the duration of one run.
It stores the URL, the domain, and the excerpt text Parallel returned, so a
claim can be rejected either for citing a URL that was never seen or for
attaching an excerpt that does not appear in the retrieved text.
"""

from __future__ import annotations

import re
from contextvars import ContextVar
from dataclasses import dataclass, field
from urllib.parse import urlparse


_WHITESPACE = re.compile(r"\s+")


def normalise_url(url: str) -> str:
    """Compare URLs without being defeated by a trailing slash or scheme case."""
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    return f"{host}{path}"


def normalise_text(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip().lower()


@dataclass
class RetrievedSource:
    url: str
    domain: str
    excerpts: tuple[str, ...]
    provider: str
    retrieval_id: str


@dataclass
class CitationRegistry:
    """What Parallel actually returned during one investigation."""

    sources: dict[str, RetrievedSource] = field(default_factory=dict)
    calls: list[dict[str, object]] = field(default_factory=list)

    def record_search(self, payload: dict) -> None:
        self.calls.append(
            {
                "provider": payload.get("provider"),
                "retrieval_id": payload.get("search_id"),
                "result_count": len(payload.get("results") or []),
            }
        )
        for result in payload.get("results") or []:
            url = str(result.get("url") or "")
            if not url:
                continue
            key = normalise_url(url)
            excerpts = tuple(str(item) for item in (result.get("excerpts") or []) if str(item).strip())
            existing = self.sources.get(key)
            if existing:
                self.sources[key] = RetrievedSource(
                    url=existing.url,
                    domain=existing.domain,
                    excerpts=existing.excerpts + excerpts,
                    provider=existing.provider,
                    retrieval_id=existing.retrieval_id,
                )
                continue
            host = (urlparse(url).hostname or "").lower()
            self.sources[key] = RetrievedSource(
                url=url,
                domain=host,
                excerpts=excerpts,
                provider=str(payload.get("provider") or "parallel_search_v1"),
                retrieval_id=str(payload.get("search_id") or ""),
            )

    def record_task(self, payload: dict) -> None:
        """Parallel Task cites its basis; record those URLs the same way."""
        self.calls.append(
            {
                "provider": payload.get("provider"),
                "retrieval_id": payload.get("run_id"),
                "result_count": len(payload.get("basis") or []),
            }
        )
        for item in payload.get("basis") or []:
            for url in re.findall(r"https?://[^\s'\"<>)\]]+", str(item)):
                key = normalise_url(url)
                if key in self.sources:
                    continue
                host = (urlparse(url).hostname or "").lower()
                self.sources[key] = RetrievedSource(
                    url=url,
                    domain=host,
                    excerpts=(str(item),),
                    provider=str(payload.get("provider") or "parallel_task_v1"),
                    retrieval_id=str(payload.get("run_id") or ""),
                )

    def lookup(self, url: str) -> RetrievedSource | None:
        return self.sources.get(normalise_url(url))

    def supports_excerpt(self, url: str, excerpt: str) -> bool:
        """True when the excerpt really appears in what Parallel returned for that URL."""
        source = self.lookup(url)
        if source is None:
            return False
        needle = normalise_text(excerpt)
        if not needle:
            return False
        return any(needle in normalise_text(text) for text in source.excerpts)

    @property
    def domains(self) -> set[str]:
        return {source.domain for source in self.sources.values() if source.domain}


_ACTIVE: ContextVar[CitationRegistry | None] = ContextVar("citation_registry", default=None)


def start_registry() -> CitationRegistry:
    registry = CitationRegistry()
    _ACTIVE.set(registry)
    return registry


def active_registry() -> CitationRegistry | None:
    return _ACTIVE.get()
