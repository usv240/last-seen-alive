"""Code-side Parallel surfaces: verification and follow-up, never model-chosen.

Three of Parallel's six surfaces are used by deterministic code rather than by an
agent, because each one exists to *check* or *outlast* the model's work:

  Extract API    — re-open the pages a decisive claim cites and confirm the
                   quoted text is on the live page, not only in a search snippet.
  Task Group API — fan out one falsification run per surviving candidate, so
                   every candidate is attacked independently and in parallel.
  Monitor API    — when the gate abstains, leave a standing query on the open web
                   so the archive hears about newly digitised material later.

Putting these in code is the point. A model that both gathers evidence and
decides whether the evidence checks out can talk itself into either answer.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from .citation_registry import CitationRegistry, normalise_text
from .parallel_client import client, current_session

#: Hard ceiling on pages re-opened per investigation. Extract is a live fetch;
#: an unbounded audit would make a demo unusable and the cost unpredictable.
MAX_AUDITED_URLS = 8

#: Ceiling on candidates fanned out for falsification.
MAX_FALSIFIED_CANDIDATES = 4


@dataclass(frozen=True, slots=True)
class AuditedSource:
    url: str
    excerpt_present_on_live_page: bool
    page_title: str | None
    publish_date: str | None
    note: str


def audit_citations_with_extract(
    citations: Sequence[tuple[str, str]],
) -> dict[str, Any]:
    """Re-open cited pages and check each quoted excerpt against the live text.

    `citations` is a sequence of (url, excerpt) pairs taken from decisive claims.
    A search snippet is Parallel's summary of a page; this asks Parallel to fetch
    the page itself. An excerpt that survives both is quoted text we have seen in
    context, which is a materially stronger claim than "it appeared in a snippet".

    Returns a report. It never mutates a claim: `evidence_builder` decides what to
    do with the result, and a failed audit only ever *weakens* a citation.
    """

    unique: dict[str, str] = {}
    for url, excerpt in citations:
        if url and url not in unique:
            unique[url] = excerpt
        if len(unique) >= MAX_AUDITED_URLS:
            break
    if not unique:
        return {
            "provider": "parallel_extract_v1",
            "status": "skipped",
            "reason": "no decisive citation required auditing",
            "audited": [],
        }

    session_id = current_session()
    response = client().extract(
        urls=list(unique),
        objective=(
            "Confirm whether the quoted historical text appears on this page, and "
            "capture the surrounding context for an archivist to read."
        ),
        **({"session_id": session_id} if session_id else {}),
        advanced_settings={
            "full_content": True,
            "excerpt_settings": {"max_chars_per_result": 8_000},
        },
    )

    audited: list[dict[str, Any]] = []
    by_url = {result.url: result for result in response.results}
    for url, excerpt in unique.items():
        result = by_url.get(url)
        if result is None:
            audited.append(
                asdict(
                    AuditedSource(
                        url=url,
                        excerpt_present_on_live_page=False,
                        page_title=None,
                        publish_date=None,
                        note="page could not be re-opened at audit time",
                    )
                )
            )
            continue
        haystack = normalise_text(
            " ".join([result.full_content or "", *(result.excerpts or [])])
        )
        needle = normalise_text(excerpt)
        present = bool(needle) and (needle in haystack or _phrase_overlap(needle, haystack))
        audited.append(
            asdict(
                AuditedSource(
                    url=url,
                    excerpt_present_on_live_page=present,
                    page_title=result.title,
                    publish_date=result.publish_date,
                    note=(
                        "quoted text found in the live page"
                        if present
                        else "quoted text not found in the live page at audit time"
                    ),
                )
            )
        )

    return {
        "provider": "parallel_extract_v1",
        "status": "completed",
        "extract_id": response.extract_id,
        "session_id": response.session_id,
        "pages_requested": len(unique),
        "pages_returned": len(response.results),
        "errors": [str(error) for error in (response.errors or [])],
        "audited": audited,
    }


def _phrase_overlap(needle: str, haystack: str, *, window: int = 12) -> bool:
    """Accept a long quotation whose page has different whitespace or ellipses.

    An exact substring test is too brittle for scanned trade papers, where a
    snippet often stitches two lines together. This requires a run of `window`
    consecutive words from the excerpt to appear verbatim in the page, which is
    still far stronger than a keyword match and cannot be satisfied by chance.
    """
    words = needle.split()
    if len(words) < window:
        return False
    return any(
        " ".join(words[index : index + window]) in haystack
        for index in range(len(words) - window + 1)
    )


def falsify_candidates_with_task_group(
    candidates: Sequence[dict[str, Any]], *, visual_summary: str
) -> dict[str, Any]:
    """Attack every surviving candidate at once, one Parallel Task run each.

    The Skeptic agent argues against candidates in sequence, sharing one context
    window, and its later attacks inherit whatever it concluded earlier. A task
    group gives each candidate an independent researcher that has never seen the
    others, which is what makes a surviving candidate mean something.
    """

    shortlist = list(candidates)[:MAX_FALSIFIED_CANDIDATES]
    if not shortlist:
        return {
            "provider": "parallel_task_group_v1",
            "status": "skipped",
            "reason": "no candidate survived compilation",
            "verdicts": [],
        }

    api = client()
    group = api.task_group.create(metadata={"workflow": "last-seen-alive-falsification"})
    inputs = [
        {
            "input": (
                f"Attempt to DISPROVE this identification of an unidentified archival film "
                f"fragment. Candidate: {candidate.get('label') or candidate.get('title')}. "
                f"Observed in the fragment: {visual_summary[:2_000]}. "
                f"Look specifically for: a release date incompatible with the visible film "
                f"stock or costume period; a different studio or country of origin; a "
                f"performer whose career does not overlap the claimed date; the same "
                f"intertitle or plot phrasing appearing in a different film; and any "
                f"competing attribution by an archive or film historian. "
                f"Report what you found with sources. If you cannot disprove it, say so "
                f"plainly and list what you checked. Do not argue for the candidate."
            ),
            "processor": "base",
            "metadata": {"candidate_id": str(candidate.get("candidate_id", "unknown"))},
        }
        for candidate in shortlist
    ]
    api.task_group.add_runs(
        group.task_group_id,
        inputs=inputs,
        default_task_spec={
            "output_schema": {
                "type": "json",
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "disproved": {
                            "type": "boolean",
                            "description": "True only if cited evidence rules the candidate out.",
                        },
                        "contradictions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Each cited fact that argues against the candidate.",
                        },
                        "checked_but_consistent": {"type": "array", "items": {"type": "string"}},
                        "unresolved": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["disproved", "contradictions"],
                },
            }
        },
    )

    verdicts: list[dict[str, Any]] = []
    try:
        for event in api.task_group.get_runs(
            group.task_group_id, include_output=True, include_input=False
        ):
            record = _run_event_to_verdict(event)
            if record is not None:
                verdicts.append(record)
            if len(verdicts) >= len(shortlist):
                break
    except Exception as exc:  # pragma: no cover - transport-level
        return {
            "provider": "parallel_task_group_v1",
            "status": "partial",
            "task_group_id": group.task_group_id,
            "reason": f"stream ended early ({type(exc).__name__})",
            "verdicts": verdicts,
        }

    return {
        "provider": "parallel_task_group_v1",
        "status": "completed",
        "task_group_id": group.task_group_id,
        "candidates_attacked": len(shortlist),
        "verdicts": verdicts,
    }


def _run_event_to_verdict(event: Any) -> dict[str, Any] | None:
    run = getattr(event, "run", None)
    if run is None:
        return None
    status = str(getattr(run, "status", "") or "")
    if status not in {"completed", "failed", "cancelled"}:
        return None
    output = getattr(event, "output", None)
    metadata = getattr(run, "metadata", None) or {}
    return {
        "run_id": str(getattr(run, "run_id", "") or ""),
        "candidate_id": str(metadata.get("candidate_id", "unknown")),
        "status": status,
        "content": getattr(output, "content", None),
        "basis": [str(item) for item in (getattr(output, "basis", None) or [])],
    }


def open_cold_case_monitor(
    *, fragment_label: str, rare_strings: Iterable[str], frequency: str = "weekly"
) -> dict[str, Any]:
    """Leave a standing open-web query for a fragment the evidence could not identify.

    An abstention is the correct answer today and the wrong answer forever. Archives
    digitise continuously; the trade paper that names this fragment may go online
    next year. A monitor turns "we do not know" into "we are still looking", which
    is the difference between triage and a dead end.
    """

    probes = [item.strip() for item in rare_strings if item and item.strip()][:5]
    if not probes:
        return {
            "provider": "parallel_monitor_v1",
            "status": "skipped",
            "reason": "the fragment yielded no rare string distinctive enough to watch",
        }

    monitor = client().monitor.create(
        type="event_stream",
        frequency=frequency,
        processor="base",
        settings={
            "objective": (
                f"Watch for newly published or newly digitised material that could "
                f"identify an unidentified archival film fragment ({fragment_label}). "
                f"Report only new sources that quote, reproduce, or catalogue any of "
                f"these exact strings observed in the fragment: "
                + "; ".join(f'"{probe}"' for probe in probes)
                + ". Ignore sources already known before this monitor was created."
            ),
            "search_queries": [f'"{probe}"' for probe in probes[:3]],
        },
        metadata={"workflow": "last-seen-alive-cold-case", "fragment": fragment_label[:120]},
    )
    return {
        "provider": "parallel_monitor_v1",
        "status": "watching",
        "monitor_id": str(getattr(monitor, "monitor_id", "") or getattr(monitor, "id", "")),
        "frequency": frequency,
        "watched_strings": probes,
        "meaning": (
            "This fragment stays unidentified. The archive is notified if new open-web "
            "material quotes one of these strings."
        ),
    }


_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]{2,}")


def rare_strings_from_clues(visual_clues: Any, *, limit: int = 5) -> list[str]:
    """Pick the strings worth watching from the Visual Examiner's typed output.

    Prefers whole transcribed intertitles, which are the only fragment text long
    enough for a monitor to match without constant false positives.
    """

    found: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, str):
            text = node.strip()
            if len(text) >= 18 and len(_WORD.findall(text)) >= 4:
                found.append(text[:180])
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)

    walk(visual_clues)
    seen: set[str] = set()
    unique: list[str] = []
    for item in found:
        key = normalise_text(item)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    unique.sort(key=len, reverse=True)
    return unique[:limit]


def decisive_citations(registry: CitationRegistry, claims: Iterable[Any]) -> list[tuple[str, str]]:
    """Collect (url, excerpt) pairs worth re-opening: cited by a decisive claim."""
    pairs: list[tuple[str, str]] = []
    for claim in claims:
        for source in getattr(claim, "sources", ()) or ():
            if getattr(source, "verified", False) and registry.lookup(source.url) is not None:
                pairs.append((source.url, source.excerpt))
    return pairs
