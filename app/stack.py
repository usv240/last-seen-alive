"""Every sponsor surface this product runs on, with the line of code that calls it.

This is the single source of truth for the stack ribbon shown on every page, for
`GET /v1/stack`, and for the submission evidence file. It exists so that the
claim "we use these services" is checkable rather than asserted: each entry names
the module and function that makes the call, and the live health probe reports
whether that path actually works right now.

`required` marks a service the workflow cannot run without. Remove Gemini and
nothing can read the fragment; remove Parallel Search and there is no open web,
so the investigation stops rather than answering from model memory.
"""

from __future__ import annotations

from typing import Any

GOOGLE_CLOUD: list[dict[str, Any]] = [
    {
        "key": "google_adk",
        "vendor": "Google Cloud",
        "name": "Agent Development Kit",
        "short": "ADK",
        "package": "google-adk",
        "required": True,
        "call_site": "app/adk_app.py",
        "role": "Runs the fixed five-role investigation as a SequentialAgent and keeps each role's output under its own state key, so every stage stays separately inspectable.",
        "health_key": "google_vertex_ai",
    },
    {
        "key": "gemini_vertex",
        "vendor": "Google Cloud",
        "name": "Gemini on Vertex AI",
        "short": "Gemini",
        "package": "google-genai",
        "required": True,
        "call_site": "app/adk_runtime.py, app/adk_app.py",
        "role": "Reads the fragment multimodally, transcribes visible text verbatim, directs the research, and argues against its own candidates. It never issues the verdict.",
        "health_key": "google_vertex_ai",
    },
    {
        "key": "vertex_controlled_generation",
        "vendor": "Google Cloud",
        "name": "Vertex AI controlled generation",
        "short": "Controlled gen",
        "package": "google-genai",
        "required": True,
        "call_site": "app/evidence_schema.py, app/adk_app.py",
        "role": "Forces the evidence compiler to emit a typed claim structure. Prose cannot be gated; a schema can.",
        "health_key": "google_vertex_ai",
    },
    {
        "key": "cloud_run",
        "vendor": "Google Cloud",
        "name": "Cloud Run",
        "short": "Cloud Run",
        "package": "-",
        "required": True,
        "call_site": "Dockerfile, infra/deploy.sh, infra/cloudrun.yaml",
        "role": "Hosts the API, the product surface, and the public demo media. Serverless, min-instance 1 so a judge never hits a cold start.",
        "health_key": "self",
    },
    {
        "key": "secret_manager",
        "vendor": "Google Cloud",
        "name": "Secret Manager",
        "short": "Secret Manager",
        "package": "-",
        "required": True,
        "call_site": "infra/deploy.sh",
        "role": "Holds the Parallel credential and the API-key signing pepper. Neither ever reaches the repository, the client, or a log line.",
        "health_key": "api_keys",
    },
]

PARALLEL: list[dict[str, Any]] = [
    {
        "key": "parallel_search",
        "vendor": "Parallel",
        "name": "Search API",
        "short": "Search",
        "package": "parallel-web",
        "required": True,
        "surface": "client.search",
        "call_site": "app/partners/parallel_research.py::search_archival_evidence",
        "used_by": "Phrase Hunter, Skeptic",
        "role": "Every open-web fact in the product enters here. Rare intertitles are searched as literal quoted strings, with long excerpts so the exact wording can be matched again later.",
        "creative_note": "Content-recycling domains are excluded at the source-policy level, so the gate's 'three independent domains' threshold cannot be satisfied by three mirrors of one plot summary.",
        "health_key": "parallel_search",
    },
    {
        "key": "parallel_task",
        "vendor": "Parallel",
        "name": "Task API",
        "short": "Task",
        "package": "parallel-web",
        "required": True,
        "surface": "client.task_run",
        "call_site": "app/partners/parallel_research.py::deep_holdings_research",
        "used_by": "Holdings Researcher",
        "role": "Multi-hop research into alternate titles, foreign releases, studio, performers and surviving elements, returned against a JSON output schema rather than as prose.",
        "creative_note": "A source policy points this one surface at library, archive, .gov and .edu domains — holdings are an institutional question — while Search deliberately stays open to the whole web.",
        "health_key": "parallel_search",
    },
    {
        "key": "parallel_extract",
        "vendor": "Parallel",
        "name": "Extract API",
        "short": "Extract",
        "package": "parallel-web",
        "required": False,
        "surface": "client.extract",
        "call_site": "app/partners/parallel_verify.py::audit_citations_with_extract",
        "used_by": "Citation audit (deterministic code)",
        "role": "Re-opens the pages that decisive claims cite and looks for the quoted text in the live document.",
        "creative_note": "This is the difference between 'a search snippet contained this' and 'the page still says this'. A citation that fails the audit is shown to the archivist but is refused by the gate — it can only ever weaken a verdict.",
        "health_key": "parallel_search",
    },
    {
        "key": "parallel_findall",
        "vendor": "Parallel",
        "name": "FindAll API",
        "short": "FindAll",
        "package": "parallel-web",
        "required": False,
        "surface": "client.beta.findall",
        "call_site": "app/partners/parallel_research.py::census_named_catalogues",
        "used_by": "Holdings Researcher",
        "role": "Enumerates the film archives, cinematheques and library catalogues worldwide whose own records list a candidate title.",
        "creative_note": "This product is forbidden from saying 'last surviving copy'. The only sentence it may write is 'no additional holding was found across these named catalogues' — and FindAll is what produces the named list that sentence depends on.",
        "health_key": "parallel_search",
    },
    {
        "key": "parallel_task_group",
        "vendor": "Parallel",
        "name": "Task Group API",
        "short": "Task Group",
        "package": "parallel-web",
        "required": False,
        "surface": "client.task_group",
        "call_site": "app/partners/parallel_verify.py::falsify_candidates_with_task_group",
        "used_by": "Adversarial fan-out (deterministic code)",
        "role": "Submits one independent falsification run per surviving candidate and collects the results together.",
        "creative_note": "The Skeptic agent attacks candidates in sequence inside one context window, so its later attacks inherit its earlier conclusions. A task group gives each candidate a researcher that has never seen the others.",
        "health_key": "parallel_search",
    },
    {
        "key": "parallel_monitor",
        "vendor": "Parallel",
        "name": "Monitor API",
        "short": "Monitor",
        "package": "parallel-web",
        "required": False,
        "surface": "client.monitor",
        "call_site": "app/partners/parallel_verify.py::open_cold_case_monitor",
        "used_by": "Cold-case watch (archivist action)",
        "role": "Leaves a standing weekly query on the open web for the fragment's rarest transcribed strings.",
        "creative_note": "An abstention is the right answer today and the wrong answer forever — archives digitise continuously. This turns 'we cannot identify it' into 'we are still looking', which is the difference between triage and a dead end.",
        "health_key": "parallel_search",
    },
]

ALL_SURFACES: list[dict[str, Any]] = GOOGLE_CLOUD + PARALLEL


def stack_report(health: dict[str, Any] | None = None) -> dict[str, Any]:
    """The stack, annotated with live status when a health snapshot is supplied."""
    health = health or {}

    def status_for(entry: dict[str, Any]) -> str:
        key = entry.get("health_key")
        if key == "self":
            return "live"
        if key == "api_keys":
            return "live" if health.get("api_keys", {}).get("ok") else "unknown"
        probe = health.get(key or "")
        if not isinstance(probe, dict):
            return "unknown"
        return "live" if probe.get("ok") else "unavailable"

    google = [{**entry, "status": status_for(entry)} for entry in GOOGLE_CLOUD]
    parallel = [{**entry, "status": status_for(entry)} for entry in PARALLEL]
    return {
        "track": "Parallel",
        "google_cloud": google,
        "parallel": parallel,
        "counts": {
            "google_cloud_surfaces": len(google),
            "parallel_surfaces": len(parallel),
            "parallel_surfaces_live": sum(entry["status"] == "live" for entry in parallel),
        },
        "policy": (
            "Every entry names the module and function that calls it. A surface reported "
            "unavailable is unavailable; nothing here is aspirational."
        ),
    }
