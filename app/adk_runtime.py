"""Executable Google ADK runtime for preset and user-supplied fragments.

The order of operations here is the product's argument. Models research; code
verifies; a human decides.

  1. The five-role ADK workflow runs. Gemini reads the fragment; Parallel Search,
     Task and FindAll supply every open-web fact.
  2. Code compiles the result into typed claims and throws away every citation
     Parallel did not actually return during this run.
  3. Code re-opens the surviving decisive citations with Parallel Extract and
     checks the quoted text against the live page. A citation that fails is kept
     visible but can no longer carry a threshold.
  4. Code fans out one independent Parallel Task Group run per candidate whose
     only job is to disprove it.
  5. Code scans every generated sentence for survival claims catalogue searching
     cannot support.
  6. A pure function reads the thresholds and returns a verdict that always
     requires an archivist.

Nothing in steps 2-6 can be talked out of its result by the model that produced
the evidence.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import asdict
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.adk_app import MODEL, root_agent
from app.evidence_builder import build as build_evidence
from app.evidence_schema import CompiledEvidence
from app.gates.identity import IdentityGate
from app.gates.language import find_prohibited_language
from app.partners.citation_registry import CitationRegistry, start_registry
from app.partners.parallel_client import start_session
from app.partners.parallel_verify import (
    audit_citations_with_extract,
    decisive_citations,
    falsify_candidates_with_task_group,
    rare_strings_from_clues,
)

APP_NAME = "last_seen_alive"

Depth = Literal["standard", "deep"]

#: Upload ceiling. A 50-second fragment at the corpus bitrate is ~12 MB; this
#: leaves generous headroom without letting one request occupy an instance.
MAX_UPLOAD_BYTES = 48 * 1024 * 1024

ACCEPTED_MEDIA_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-matroska",
    "image/jpeg",
    "image/png",
    "image/webp",
}


class InvestigationNotConfigured(RuntimeError):
    """Raised when a required live runtime is absent."""


class FragmentRejected(ValueError):
    """Raised when a supplied fragment cannot be accepted for investigation."""


def validate_runtime() -> None:
    required = ("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION", "PARALLEL_API_KEY")
    missing = [name for name in required if not os.getenv(name)]
    if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() not in {"1", "true", "yes"}:
        missing.append("GOOGLE_GENAI_USE_VERTEXAI=true")
    if missing:
        raise InvestigationNotConfigured(f"Missing live runtime configuration: {', '.join(missing)}")


def validate_fragment(*, data: bytes, media_type: str) -> None:
    """Check a user-supplied fragment before any model or partner call is made."""
    if not data:
        raise FragmentRejected("The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise FragmentRejected(
            f"The file is {len(data) // (1024 * 1024)} MB. The limit is "
            f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB — upload a short excerpt, not a whole reel."
        )
    if media_type not in ACCEPTED_MEDIA_TYPES:
        raise FragmentRejected(
            f"Unsupported media type {media_type!r}. Accepted: "
            + ", ".join(sorted(ACCEPTED_MEDIA_TYPES))
        )


async def run_development_investigation(
    *, sample_id: str, fragment_path: Path, media_type: str, provided_label: str | None
) -> dict[str, Any]:
    """Run a preset development fragment without opening the held-out split."""
    if not sample_id.startswith("D"):
        raise PermissionError(
            "Only development fragments may enter the live workflow before eval freeze."
        )
    validate_runtime()
    return await run_investigation(
        fragment=fragment_path.read_bytes(),
        media_type=media_type,
        provided_label=provided_label,
        origin=f"preset:{sample_id}",
        sample_id=sample_id,
    )


async def run_investigation(
    *,
    fragment: bytes,
    media_type: str,
    provided_label: str | None,
    origin: str,
    sample_id: str | None = None,
    depth: Depth = "standard",
) -> dict[str, Any]:
    """Investigate one fragment end to end and return the full evidence dossier.

    The gate reaches a real verdict but never a confirmed one: `human_approved`
    is false here because approving an identity is an archivist action, not an
    API call.
    """

    validate_runtime()
    started = perf_counter()
    session_id = f"lsa_{uuid.uuid4().hex[:12]}"
    parallel_session = start_session()
    registry = start_registry()

    outputs, transcript = await _run_workflow(
        fragment=fragment,
        media_type=media_type,
        provided_label=provided_label,
        sample_id=sample_id or origin,
        session_id=session_id,
    )

    compiled = _parse_compiled(outputs.get("evidence_compiler"))

    # Pass one: keep only citations Parallel actually returned, so we know which
    # pages are worth the cost of re-opening.
    evidence = build_evidence(compiled, registry)

    audit = await asyncio.to_thread(
        _audit, registry=registry, claims=evidence.claims
    )

    # Pass two: the same pure build, now with the live-audit result attached to
    # each source. Rebuilding is cheaper and clearer than mutating frozen records.
    evidence = build_evidence(compiled, registry)

    falsification = await asyncio.to_thread(
        _falsify,
        depth=depth,
        candidates=evidence.as_dict()["candidates"],
        visual_summary=str(outputs.get("visual_examiner") or "")[:2_000],
    )

    language_findings = find_prohibited_language(outputs)

    gate = IdentityGate().evaluate(
        claims=evidence.claims,
        context=evidence.gate_context(human_approved=False),
    )

    cold_case = rare_strings_from_clues(outputs.get("visual_examiner"))

    return {
        "status": "completed",
        "session_id": session_id,
        "parallel_session_id": parallel_session,
        "sample_id": sample_id,
        "origin": origin,
        "model": MODEL,
        "agent_runtime": "google-adk",
        "depth": depth,
        "latency_ms": round((perf_counter() - started) * 1000),
        "outputs": outputs,
        "evidence": evidence.as_dict(),
        "parallel_retrieval": {
            "session_id": parallel_session,
            "calls": registry.calls,
            "sources_returned": len(registry.sources),
            "independent_domains": sorted(registry.domains),
            "surfaces_used": sorted(
                {str(call.get("provider")) for call in registry.calls if call.get("provider")}
            ),
        },
        "citation_audit": audit,
        "falsification": falsification,
        "language_findings": language_findings,
        "cold_case": {
            "eligible": gate.verdict in {"abstain", "candidates"} and bool(cold_case),
            "watchable_strings": cold_case,
            "how": "POST /v1/watch to leave a standing Parallel Monitor on these strings.",
        },
        "transcript": transcript,
        "gate": {
            **asdict(gate),
            "passed": list(gate.passed),
            "failed": list(gate.failed),
        },
        "requires_human": True,
    }


async def _run_workflow(
    *,
    fragment: bytes,
    media_type: str,
    provided_label: str | None,
    sample_id: str,
    session_id: str,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    user_id = "public_judge"
    sessions = InMemorySessionService()
    await sessions.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
        state={"sample_id": sample_id, "provided_label": provided_label or "none"},
    )
    runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=sessions)
    prompt = (
        f"Investigate fragment {sample_id}. The only supplied catalogue label is "
        f"{provided_label!r}. Preserve citations, distinguish observation from inference, and "
        "do not issue an identity verdict; deterministic code and an archivist own that decision."
    )
    message = types.Content(
        role="user",
        parts=[
            types.Part(text=prompt),
            types.Part.from_bytes(data=fragment, mime_type=media_type),
        ],
    )
    transcript: list[dict[str, str]] = []
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=message
    ):
        parts = getattr(getattr(event, "content", None), "parts", None) or []
        text_parts = [part.text for part in parts if getattr(part, "text", None)]
        if text_parts:
            transcript.append(
                {"author": str(getattr(event, "author", "agent")), "text": "\n".join(text_parts)}
            )

    completed = await sessions.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    state = completed.state if completed else {}
    outputs = {
        "visual_examiner": state.get("visual_clues"),
        "phrase_hunter": state.get("phrase_evidence"),
        "holdings_researcher": state.get("holdings_evidence"),
        "skeptic": state.get("skeptic_evidence"),
        "evidence_compiler": state.get("compiled_evidence"),
    }
    return outputs, transcript


def _audit(*, registry: CitationRegistry, claims: Any) -> dict[str, Any]:
    """Re-open decisive citations with Parallel Extract; never fail the run for it.

    A verification step that can take the whole investigation down with it is a
    liability. If Extract is unavailable, sources keep their unaudited state and
    the response says the audit did not run.
    """
    citations = decisive_citations(registry, claims)
    if not citations:
        return {
            "provider": "parallel_extract_v1",
            "status": "skipped",
            "reason": "no decisive citation survived compilation",
            "audited": [],
        }
    try:
        report = audit_citations_with_extract(citations)
    except Exception as exc:
        return {
            "provider": "parallel_extract_v1",
            "status": "unavailable",
            "reason": f"the citation audit could not run ({type(exc).__name__}); "
            "sources remain unaudited rather than being marked verified",
            "audited": [],
        }
    for entry in report.get("audited", []):
        registry.record_live_audit(
            str(entry.get("url", "")), bool(entry.get("excerpt_present_on_live_page"))
        )
    return report


def _falsify(*, depth: Depth, candidates: list[dict[str, Any]], visual_summary: str) -> dict[str, Any]:
    if depth != "deep":
        return {
            "provider": "parallel_task_group_v1",
            "status": "not_requested",
            "reason": "Send depth=deep to fan out one independent falsification run per candidate.",
            "verdicts": [],
        }
    if not candidates:
        return {
            "provider": "parallel_task_group_v1",
            "status": "skipped",
            "reason": "no candidate survived compilation",
            "verdicts": [],
        }
    try:
        return falsify_candidates_with_task_group(candidates, visual_summary=visual_summary)
    except Exception as exc:
        return {
            "provider": "parallel_task_group_v1",
            "status": "unavailable",
            "reason": f"the falsification fan-out could not run ({type(exc).__name__})",
            "verdicts": [],
        }


def _parse_compiled(raw: Any) -> CompiledEvidence:
    """Read the compiler's output, failing to an empty structure rather than a guess.

    An unparseable compiler result must not become an identification. Empty
    evidence makes the gate abstain, which is the safe direction.
    """
    if isinstance(raw, CompiledEvidence):
        return raw
    if isinstance(raw, dict):
        try:
            return CompiledEvidence.model_validate(raw)
        except Exception:
            return CompiledEvidence()
    if isinstance(raw, str) and raw.strip():
        try:
            return CompiledEvidence.model_validate_json(raw)
        except Exception:
            return CompiledEvidence()
    return CompiledEvidence()
