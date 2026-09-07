"""Agent-facing Parallel tools: the only open-web path in Last Seen Alive.

Three of Parallel's six product surfaces are exposed to the ADK agents as tools,
because they are *research* actions a reasoning agent should choose when to take:

  Search API    — find dated evidence for a literal rare string.
  Task API      — multi-hop holdings and alternate-title research.
  FindAll API   — enumerate the named institutions that hold a candidate title.

The other three (Extract, Task Group, Monitor) are verification and follow-up
actions that code performs, not the model. They live in `parallel_verify.py`.
"""

from __future__ import annotations

from typing import Any

from .citation_registry import active_registry
from .parallel_client import (
    ARCHIVAL_SOURCE_DOMAINS,
    RECYCLED_CONTENT_DOMAINS,
    client,
    current_session,
)

#: Structured shape we ask Parallel Task to return, so holdings research arrives
#: as fields the evidence compiler can copy rather than prose it must re-read.
HOLDINGS_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "candidate_title": {"type": "string", "description": "Best-evidenced title."},
        "release_year": {"type": "string", "description": "Year, or empty if unevidenced."},
        "studio_or_producer": {"type": "string"},
        "country": {"type": "string"},
        "alternate_titles": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Foreign, working, reissue and formerly-supplied titles found.",
        },
        "named_catalogues_searched": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Institutions or catalogues actually consulted in this research.",
        },
        "holdings_found": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "institution": {"type": "string"},
                    "country": {"type": "string"},
                    "element_or_format": {"type": "string"},
                    "catalogue_url": {"type": "string"},
                },
            },
            "description": "Each surviving element reported by a named catalogue.",
        },
        "restoration_notices": {"type": "array", "items": {"type": "string"}},
        "contradicting_evidence": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Anything found that argues against the candidate.",
        },
        "coverage_gaps": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Catalogues that could not be searched, and why.",
        },
    },
    "required": ["candidate_title", "named_catalogues_searched", "holdings_found"],
}


def search_archival_evidence(objective: str, search_queries: list[str]) -> dict[str, Any]:
    """Search exact phrases/proper nouns and return Parallel's cited excerpts.

    Args:
        objective: A self-contained archival identification research objective.
        search_queries: Two to five short queries. Preserve rare phrases in quotation marks.
    """

    if not 2 <= len(search_queries) <= 5:
        raise ValueError("Parallel Search requires two to five diverse queries")
    if any(len(query) > 200 for query in search_queries):
        raise ValueError("Parallel Search queries must not exceed 200 characters")
    session_id = current_session()
    response = client().search(
        objective=objective[:5_000],
        search_queries=search_queries,
        mode="advanced",
        max_chars_total=60_000,
        **({"session_id": session_id} if session_id else {}),
        advanced_settings={
            "max_results": 10,
            # A long excerpt is what lets a verbatim intertitle be matched against
            # retrieved text later. Short snippets lose the exact wording that is
            # the whole point of searching a rare phrase.
            "excerpt_settings": {"max_chars_per_result": 6_000},
            # Search stays open to the whole web; only sites that recycle each
            # other's plot summaries are excluded, so that "three independent
            # domains" cannot be satisfied by three copies of one paragraph.
            "source_policy": {"exclude_domains": list(RECYCLED_CONTENT_DOMAINS)},
        },
    )
    payload = {
        "provider": "parallel_search_v1",
        "search_id": response.search_id,
        "session_id": response.session_id,
        "results": [
            {
                "url": result.url,
                "title": result.title,
                "publish_date": result.publish_date,
                "excerpts": list(result.excerpts),
            }
            for result in response.results
        ],
        "warnings": [str(warning) for warning in (response.warnings or [])],
        "usage": [str(item) for item in (response.usage or [])],
    }
    # Record what was really returned so a claim cannot cite a URL Parallel
    # never produced. See app/partners/citation_registry.py.
    registry = active_registry()
    if registry is not None:
        registry.record_search(payload)
    return payload


def deep_holdings_research(research_question: str) -> dict[str, Any]:
    """Investigate alternate titles and worldwide holdings through Parallel Task API.

    Args:
        research_question: Candidate-specific question naming titles, dates, studios, and the
            catalogues or regions that still need checking.
    """

    api = client()
    run = api.task_run.create(
        input=research_question[:15_000],
        processor="pro-fast",
        task_spec={"output_schema": {"type": "json", "json_schema": HOLDINGS_OUTPUT_SCHEMA}},
        # Holdings are an institutional question, so this one surface is pointed
        # at institutional sources. Search deliberately is not.
        source_policy={"include_domains": list(ARCHIVAL_SOURCE_DOMAINS)},
        metadata={"workflow": "last-seen-alive-holdings"},
    )
    result = api.task_run.result(run.run_id, api_timeout=600)
    output = result.output
    payload = {
        "provider": "parallel_task_v1",
        "run_id": run.run_id,
        "interaction_id": run.interaction_id,
        "processor": "pro-fast",
        "content": getattr(output, "content", None),
        "basis": [str(item) for item in getattr(output, "basis", [])],
    }
    registry = active_registry()
    if registry is not None:
        registry.record_task(payload)
    return payload


def census_named_catalogues(candidate_title: str, release_year: str) -> dict[str, Any]:
    """Enumerate the film archives and catalogues that list a candidate title.

    Use this once a candidate is plausible. It returns a list of named institutions,
    which is the only basis on which this system is permitted to describe search
    coverage. Never use it to claim a film is rare, unique, or lost.

    Args:
        candidate_title: The candidate film title to look for in archive holdings.
        release_year: Release year if evidenced, otherwise an empty string.
    """

    label = f"{candidate_title} ({release_year})" if release_year else candidate_title
    api = client()
    run = api.beta.findall.create(
        entity_type="film archives, cinematheques, and library moving-image catalogues",
        generator="base",
        objective=(
            f"Find moving-image archives, cinematheques, film institutes and library "
            f"catalogues anywhere in the world whose public catalogue lists a surviving "
            f"element, print, negative, or digitisation of the film {label}. Report the "
            f"institution, its country, the element or format described, and the "
            f"catalogue record URL. Report only institutions whose own catalogue or "
            f"official publication says so."
        ),
        match_conditions=[
            {
                "name": "catalogue_record_exists",
                "description": (
                    f"The institution's own public catalogue, finding aid, or official "
                    f"publication contains a record for {label}, or for a documented "
                    f"alternate or foreign-release title of it."
                ),
            },
            {
                "name": "moving_image_element_described",
                "description": (
                    "The record describes an actual moving-image element (nitrate or "
                    "safety print, negative, dupe, reel fragment, or digitisation), not "
                    "merely a poster, still, script, review, or press clipping."
                ),
            },
        ],
        match_limit=12,
        metadata={"workflow": "last-seen-alive-catalogue-census"},
    )
    result = api.beta.findall.result(run.findall_id)
    candidates = getattr(result, "candidates", None) or []
    institutions: list[dict[str, Any]] = []
    for entry in candidates:
        institutions.append(
            {
                "name": str(getattr(entry, "name", "") or ""),
                "url": str(getattr(entry, "url", "") or ""),
                "match_status": str(getattr(entry, "match_status", "") or ""),
                "fields": _plain(getattr(entry, "enrichments", None))
                or _plain(getattr(entry, "fields", None)),
            }
        )
    payload = {
        "provider": "parallel_findall_v1beta",
        "findall_id": run.findall_id,
        "generator": run.generator,
        "queried_title": label,
        "institutions": institutions,
        "permitted_statement": (
            "No additional holding was found across these named catalogues as of this "
            "search date."
        ),
        "prohibited_statement": (
            "This census can never establish that a print is the last, only, or sole "
            "surviving copy."
        ),
    }
    registry = active_registry()
    if registry is not None:
        registry.record_findall(payload)
    return payload


def _plain(value: Any) -> Any:
    """Convert an SDK model to plain JSON-safe data without assuming its shape."""
    if value is None:
        return None
    if hasattr(value, "to_dict"):
        try:
            return value.to_dict()
        except Exception:
            return str(value)
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return str(value)
