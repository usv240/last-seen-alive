"""Executable Google ADK runtime for development fragments only."""

from __future__ import annotations

import os
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.adk_app import MODEL, root_agent
from app.gates.identity import IdentityGate

APP_NAME = "last_seen_alive"


class InvestigationNotConfigured(RuntimeError):
    """Raised when a required live runtime is absent."""


def validate_runtime() -> None:
    required = ("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION", "PARALLEL_API_KEY")
    missing = [name for name in required if not os.getenv(name)]
    if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() not in {"1", "true", "yes"}:
        missing.append("GOOGLE_GENAI_USE_VERTEXAI=true")
    if missing:
        raise InvestigationNotConfigured(f"Missing live runtime configuration: {', '.join(missing)}")


async def run_development_investigation(
    *, sample_id: str, fragment_path: Path, media_type: str, provided_label: str | None
) -> dict[str, Any]:
    """Run the real four-role workflow without opening the held-out split.

    The model and Parallel produce research evidence. Until a typed claim parser and
    archivist approval exist, the deterministic gate deliberately receives no decisive
    claims and therefore cannot emit a probable identity.
    """

    validate_runtime()
    if not sample_id.startswith("D"):
        raise PermissionError("Only development fragments may enter the live workflow before eval freeze.")
    fragment = fragment_path.read_bytes()
    session_id = f"lsa_{uuid.uuid4().hex[:12]}"
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
        f"Investigate development fragment {sample_id}. The only supplied catalogue label is "
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
    }
    gate = IdentityGate().evaluate(
        claims=(),
        context={
            "candidates": (),
            "decisive_clue_families": (),
            "temporal_compatibility": False,
            "entity_compatibility": False,
            "human_approved": False,
        },
    )
    return {
        "status": "completed",
        "session_id": session_id,
        "sample_id": sample_id,
        "model": MODEL,
        "agent_runtime": "google-adk",
        "research_runtime": "parallel-search-and-task",
        "outputs": outputs,
        "transcript": transcript,
        "gate": {
            **asdict(gate),
            "passed": list(gate.passed),
            "failed": list(gate.failed),
        },
        "requires_human": True,
    }
