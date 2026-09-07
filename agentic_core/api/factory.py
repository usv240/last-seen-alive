"""FastAPI factory implementing the common public contract from PLAN/03."""

from __future__ import annotations

import secrets
import threading
from collections import defaultdict
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from agentic_core.api.keys import (
    ApiKeyRecord,
    ApiKeyStore,
    KeyTier,
    authenticate_key,
    mint_key,
)

IntegrationHealth = Callable[[], Awaitable[Mapping[str, Mapping[str, object]]]]
LatestEvaluation = Callable[[], Awaitable[Mapping[str, object]]]


@dataclass(frozen=True, slots=True)
class ApiHooks:
    integration_health: IntegrationHealth
    latest_evaluation: LatestEvaluation


class KeyRequest(BaseModel):
    tier: KeyTier = Field(
        default="judge",
        description="`judge` mints a 60-day key with no email. `evaluation` requires an email.",
    )
    email: str | None = Field(
        default=None, description="Required for the `evaluation` tier only."
    )


class UsageCounter:
    """Best-effort per-key daily counter.

    This instance counts what it served. Cloud Run may run several instances, so
    the true ceiling is the limit multiplied by the number of live instances. We
    say so in the response headers rather than implying a distributed quota we do
    not have; a durable counter is the upgrade path if abuse ever appears.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._day = datetime.now(UTC).date()
        self._counts: dict[str, int] = defaultdict(int)

    def charge(self, key_id: str, limit: int) -> tuple[int, int]:
        """Record one call. Returns (used, remaining); raises when over the limit."""
        with self._lock:
            today = datetime.now(UTC).date()
            if today != self._day:
                self._day = today
                self._counts.clear()
            used = self._counts[key_id] + 1
            if used > limit:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "code": "daily_limit_reached",
                        "message": f"This key has used its {limit} calls for today (UTC).",
                        "fix": "Wait for the UTC day to roll over, or mint another key at POST /v1/keys.",
                    },
                )
            self._counts[key_id] = used
            return used, limit - used


def create_app(
    *,
    title: str,
    key_store: ApiKeyStore,
    key_pepper: bytes,
    hooks: ApiHooks,
    description: str = "",
    version: str = "1.0.0",
    max_body_bytes: int | None = None,
    cors_origins: Sequence[str] = ("*",),
) -> FastAPI:
    app = FastAPI(
        title=title,
        version=version,
        description=description,
        openapi_tags=[
            {"name": "Access", "description": "Mint an API key. No signup, no email for judges."},
            {"name": "Health", "description": "Liveness and per-integration runtime status."},
            {"name": "Presets", "description": "Public demo fragments: metadata, media, and results."},
            {"name": "Investigate", "description": "Run the agent workflow on a preset or your own file."},
            {"name": "Evaluation", "description": "Benchmark corpus state and frozen results."},
        ],
    )
    usage = UsageCounter()

    # Browser clients on another origin have to be able to call this. Every
    # request is authorised by a Bearer token and nothing uses cookies, so
    # there is no ambient authority for a cross-origin page to borrow and no
    # CSRF surface to open by allowing it.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["X-Fragment-SHA256", "X-Credit"],
        max_age=3600,
    )

    if max_body_bytes is not None:

        @app.middleware("http")
        async def limit_body_size(request: Request, call_next):
            """Refuse an oversized upload before its body is read.

            Starlette spools a multipart body to a temporary file once it passes
            1 MB, and on Cloud Run the filesystem is memory-backed -- so by the
            time a handler could measure the upload, the bytes are already in
            RAM. Checking the declared length first is what keeps a large POST
            from being an out-of-memory button.

            A missing or lying Content-Length still reaches the handler, which
            reads at most the limit and rejects anything longer. This is the
            cheap first line, not the only one.
            """
            declared = request.headers.get("content-length")
            if declared and declared.isdigit() and int(declared) > max_body_bytes:
                return JSONResponse(
                    status_code=413,
                    content={
                        "ok": False,
                        "error": {
                            "code": "request_too_large",
                            "message": (
                                f"The request body is {int(declared) // (1024 * 1024)} MB. "
                                f"The limit is {max_body_bytes // (1024 * 1024)} MB."
                            ),
                            "fix": "Upload a short excerpt rather than a whole reel.",
                            "docs": "/docs",
                        },
                        "meta": {"request_id": "req_" + secrets.token_hex(10)},
                    },
                )
            return await call_next(request)

    async def require_key(
        request: Request, authorization: str | None = Header(default=None)
    ) -> ApiKeyRecord:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "missing_api_key",
                    "message": "A Bearer API key is required.",
                    "fix": "POST /v1/keys with {\"tier\":\"judge\"} and send the key as `Authorization: Bearer <key>`.",
                },
            )
        record = authenticate_key(
            authorization.removeprefix("Bearer ").strip(),
            pepper=key_pepper,
            store=key_store,
        )
        if record is None:
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "invalid_api_key",
                    "message": "The API key is malformed, not signed by this service, or expired.",
                    "fix": "Mint a fresh key at POST /v1/keys.",
                },
            )
        used, remaining = usage.charge(record.key_id, record.daily_limit)
        request.state.api_key = record
        request.state.usage = {"used_today": used, "remaining_today": remaining}
        return record

    @app.exception_handler(HTTPException)
    async def http_error(_request: object, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        default_code = "unauthorized" if exc.status_code == 401 else "request_error"
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "ok": False,
                "error": {
                    "code": str(detail.get("code", default_code)),
                    "message": str(detail.get("message", exc.detail)),
                    "fix": str(
                        detail.get(
                            "fix",
                            "Correct the request or required runtime configuration, then retry.",
                        )
                    ),
                    "docs": "/docs",
                },
                "meta": {"request_id": "req_" + secrets.token_hex(10)},
            },
        )

    @app.get("/health", tags=["Health"], summary="Liveness")
    async def health() -> dict[str, object]:
        return {"ok": True, "data": {"status": "healthy"}}

    @app.get(
        "/health/integrations",
        tags=["Health"],
        summary="Per-integration runtime status",
        description=(
            "Reports whether each sponsor runtime is genuinely reachable from this service. "
            "A failing integration is reported as failing; nothing here is optimistic."
        ),
    )
    async def health_integrations() -> dict[str, object]:
        return {"ok": True, "data": {"integrations": await hooks.integration_health()}}

    @app.post(
        "/v1/keys",
        tags=["Access"],
        summary="Mint an API key",
        description=(
            "Returns a signed, stateless key. Judges need no email. The key is shown once and "
            "is never stored server-side; it verifies on every instance and survives restarts."
        ),
    )
    async def create_key(request: KeyRequest) -> dict[str, object]:
        if request.tier == "evaluation" and not request.email:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "email_required",
                    "message": "An email is required for evaluation keys.",
                    "fix": 'Use {"tier":"judge"} for instant no-email access.',
                },
            )
        raw, record = mint_key(tier=request.tier, pepper=key_pepper, store=key_store)
        return {
            "ok": True,
            "data": {
                "key": raw,
                "key_id": record.key_id,
                "tier": record.tier,
                "expires_at": record.expires_at.isoformat(),
                "daily_limit": record.daily_limit,
                "usage": "Send as `Authorization: Bearer <key>`.",
                "storage": "This key is not stored. It cannot be recovered or listed later.",
            },
            "meta": {"request_id": "req_" + secrets.token_hex(10)},
        }

    @app.get(
        "/v1/eval/latest",
        tags=["Evaluation"],
        summary="Latest frozen evaluation report",
    )
    async def latest_eval(_key: ApiKeyRecord = Depends(require_key)) -> dict[str, object]:
        return {"ok": True, "data": await hooks.latest_evaluation()}

    app.state.require_key = require_key
    app.state.usage = usage
    app.state.key_pepper = key_pepper
    return app
