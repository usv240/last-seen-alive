"""Cloud Run API and static product surface."""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Mapping

from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from parallel import Parallel

from agentic_core.api import ApiHooks, MemoryApiKeyStore, create_app

WEB_DIR = Path(__file__).resolve().parents[1] / "web"
PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "agentic-fleet-2026")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

_health_cache: tuple[float, Mapping[str, Mapping[str, object]]] | None = None


def _check_google() -> dict[str, object]:
    try:
        with genai.Client(vertexai=True, project=PROJECT, location=LOCATION) as client:
            model = client.models.get(model=MODEL)
        return {"ok": True, "detail": getattr(model, "name", MODEL)}
    except Exception as exc:
        return {"ok": False, "detail": type(exc).__name__}


def _check_parallel() -> dict[str, object]:
    api_key = os.environ.get("PARALLEL_API_KEY")
    if not api_key:
        return {"ok": False, "detail": "credential_not_configured"}
    try:
        result = Parallel(api_key=api_key).search(
            objective="Verify that the Parallel Search API is available.",
            search_queries=["Parallel Search API", "Parallel documentation"],
            mode="basic",
            max_results=1,
        )
        return {"ok": bool(result.search_id), "detail": result.search_id}
    except Exception as exc:
        return {"ok": False, "detail": type(exc).__name__}


async def integration_health() -> Mapping[str, Mapping[str, object]]:
    global _health_cache
    now = time.monotonic()
    if _health_cache and now - _health_cache[0] < 60:
        return _health_cache[1]
    google_result, parallel_result = await asyncio.gather(
        asyncio.to_thread(_check_google),
        asyncio.to_thread(_check_parallel),
    )
    result = {"google_vertex_ai": google_result, "parallel_search": parallel_result}
    _health_cache = (now, result)
    return result


async def latest_evaluation() -> Mapping[str, object]:
    report = Path(os.environ.get("EVAL_REPORT_PATH", "eval/reports/held-out.json"))
    if not report.exists():
        return {
            "status": "not_run",
            "reason": "The held-out split remains sealed until an eval-freeze tag exists.",
        }
    import json

    return json.loads(report.read_text(encoding="utf-8"))


pepper = os.environ.get("API_KEY_PEPPER", "local-development-only-change-before-deploy")
api = create_app(
    title="Last Seen Alive API",
    key_store=MemoryApiKeyStore(),
    key_pepper=pepper.encode("utf-8"),
    hooks=ApiHooks(integration_health=integration_health, latest_evaluation=latest_evaluation),
)


@api.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@api.post("/v1/identify")
async def identify_not_yet_enabled() -> None:
    raise HTTPException(
        status_code=503,
        detail="The live investigation path is sealed until its evaluation corpus is corrected.",
    )


api.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
app = api

