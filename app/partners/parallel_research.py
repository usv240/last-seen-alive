"""The only open-web path in Last Seen Alive: Parallel Search and Task APIs."""

from __future__ import annotations

import os
from typing import Any

from parallel import Parallel


def _client() -> Parallel:
    api_key = os.environ.get("PARALLEL_API_KEY")
    if not api_key:
        raise RuntimeError("PARALLEL_API_KEY is required; search cannot silently fall back")
    return Parallel(api_key=api_key)


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
    response = _client().search(
        objective=objective[:5_000],
        search_queries=search_queries,
        mode="advanced",
        max_results=10,
    )
    return {
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


def deep_holdings_research(research_question: str) -> dict[str, Any]:
    """Investigate alternate titles and worldwide holdings through Parallel Task API.

    Args:
        research_question: Candidate-specific question naming titles, dates, studios, and the
            catalogues or regions that still need checking.
    """

    client = _client()
    run = client.task_run.create(
        input=research_question[:15_000],
        processor="pro-fast",
        metadata={"workflow": "last-seen-alive-holdings"},
    )
    result = client.task_run.result(run.run_id, api_timeout=600)
    output = result.output
    return {
        "provider": "parallel_task_v1",
        "run_id": run.run_id,
        "interaction_id": run.interaction_id,
        "content": getattr(output, "content", None),
        "basis": [str(item) for item in getattr(output, "basis", [])],
    }

