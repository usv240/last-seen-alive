"""Cloud Run API and static product surface."""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from pydantic import BaseModel, Field

from agentic_core.api import ApiHooks, MemoryApiKeyStore, create_app
from agentic_core.api.keys import ApiKeyRecord
from app import practice as practice_register
from app import presets as preset_catalog
from app import stack as stack_catalog
from app import standards as standards_catalog
from app.partners import parallel_client

WEB_DIR = Path(__file__).resolve().parents[1] / "web"
EVAL_DIR = Path(__file__).resolve().parents[2] / "eval"
DOSSIER_DIR = EVAL_DIR / "reports" / "dossiers"
PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "agentic-fleet-2026")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

#: A healthy result is cached longer than an unhealthy one. The Parallel probe
#: costs a real search, and with a warm instance a 60-second cache would burn
#: about 1,400 searches a day proving something that had not changed. A failure
#: is re-probed quickly because that is the state an operator is waiting on.
HEALTH_TTL_OK = 900
HEALTH_TTL_FAIL = 60

_health_cache: tuple[float, Mapping[str, Mapping[str, object]]] | None = None

DESCRIPTION = """
Evidence-first identification triage for unidentified archival film fragments.

Send a fragment; get back a dossier: typed claims, the source behind each one,
the contradictions found against it, and a deterministic gate showing exactly
which evidence thresholds passed. An abstention is a valid, successful outcome
and returns HTTP 200.

**Access.** `POST /v1/keys` with `{"tier":"judge"}` returns a 60-day key with no
email and no signup. Send it as `Authorization: Bearer <key>`.

**Two ways in.** Run one of the ten public Library of Congress demo fragments
via `POST /v1/identify`, or send your own file to `POST /v1/investigate`.

**What this is not.** It is not an attribution authority. Every identification
requires an archivist; the API can never return a confirmed identity.
""".strip()


class IdentifyRequest(BaseModel):
    sample_id: str = Field(
        pattern=r"^[DH][0-9]{2}$",
        description="Preset case id, e.g. `D02`. Held-out `H*` cases return 423.",
        examples=["D02"],
    )
    depth: Literal["standard", "deep"] = Field(
        default="standard",
        description=(
            "`deep` additionally fans out one independent Parallel Task Group run per "
            "candidate whose only job is to disprove it. Slower, and much harder on a "
            "weak candidate."
        ),
    )


class WatchRequest(BaseModel):
    fragment_label: str = Field(
        max_length=120,
        description="How this fragment is known in your catalogue.",
        examples=["Unidentified reel, can 41B"],
    )
    rare_strings: list[str] = Field(
        min_length=1,
        max_length=5,
        description=(
            "Verbatim strings observed in the fragment. Take these from "
            "`cold_case.watchable_strings` on an investigation response."
        ),
    )
    frequency: Literal["daily", "weekly", "monthly"] = "weekly"


def _check_google() -> dict[str, object]:
    try:
        with genai.Client(vertexai=True, project=PROJECT, location=LOCATION) as client:
            model = client.models.get(model=MODEL)
        return {"ok": True, "detail": getattr(model, "name", MODEL)}
    except Exception as exc:
        return {"ok": False, "detail": type(exc).__name__}


def _check_parallel() -> dict[str, object]:
    if not parallel_client.is_configured():
        return {"ok": False, "detail": "credential_not_configured"}
    try:
        result = parallel_client.client().search(
            objective="Confirm the Parallel Search API is reachable with this credential.",
            search_queries=["Parallel Search API status"],
            mode="turbo",
            max_chars_total=1_000,
            advanced_settings={"max_results": 1},
        )
        return {"ok": bool(result.search_id), "detail": result.search_id}
    except Exception as exc:
        return {"ok": False, "detail": type(exc).__name__}


async def integration_health() -> Mapping[str, Mapping[str, object]]:
    global _health_cache
    now = time.monotonic()
    if _health_cache:
        cached_at, cached = _health_cache
        healthy = all(bool(entry.get("ok")) for entry in cached.values())
        if now - cached_at < (HEALTH_TTL_OK if healthy else HEALTH_TTL_FAIL):
            return cached
    google_result, parallel_result = await asyncio.gather(
        asyncio.to_thread(_check_google),
        asyncio.to_thread(_check_parallel),
    )
    result = {
        "google_vertex_ai": google_result,
        "parallel_search": parallel_result,
        "api_keys": {
            "ok": bool(os.environ.get("API_KEY_PEPPER")),
            "detail": "signing pepper present" if os.environ.get("API_KEY_PEPPER") else "unset",
        },
    }
    _health_cache = (now, result)
    return result


async def latest_evaluation() -> Mapping[str, object]:
    report = Path(os.environ.get("EVAL_REPORT_PATH", "eval/reports/held-out.json"))
    if not report.exists():
        return {
            "status": "not_run",
            "reason": (
                "The corrected holdout remains sealed until the workflow, partner runtime, "
                "and eval-freeze tag are ready."
            ),
        }
    return json.loads(report.read_text(encoding="utf-8"))


pepper = os.environ.get("API_KEY_PEPPER", "local-development-only-change-before-deploy")

#: Transport ceiling, a little above the 48 MB file limit to allow for the
#: multipart envelope and form fields. Enforced on Content-Length before the
#: body is read; the handler still enforces the file limit on the bytes.
MAX_REQUEST_BYTES = 52 * 1024 * 1024

api = create_app(
    title="Last Seen Alive API",
    description=DESCRIPTION,
    key_store=MemoryApiKeyStore(),
    key_pepper=pepper.encode("utf-8"),
    hooks=ApiHooks(integration_health=integration_health, latest_evaluation=latest_evaluation),
    max_body_bytes=MAX_REQUEST_BYTES,
)
require_key = api.state.require_key


# ---------------------------------------------------------------- product pages

def _page(name: str) -> FileResponse:
    return FileResponse(WEB_DIR / name)


@api.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return _page("index.html")


@api.get("/presets", include_in_schema=False)
async def presets_page() -> FileResponse:
    return _page("presets.html")


@api.get("/api", include_in_schema=False)
async def api_page() -> FileResponse:
    return _page("api.html")


@api.get("/stack", include_in_schema=False)
async def stack_page() -> FileResponse:
    return _page("stack.html")


@api.get("/practice", include_in_schema=False)
async def practice_page() -> FileResponse:
    return _page("practice.html")


@api.get("/dossiers", include_in_schema=False)
async def dossiers_page() -> FileResponse:
    return _page("dossiers.html")


@api.get("/evaluation", include_in_schema=False)
async def evaluation_page() -> FileResponse:
    return _page("evaluation.html")


# ------------------------------------------------------------------- the stack

@api.get(
    "/v1/stack",
    tags=["Health"],
    summary="Every sponsor service this product runs on",
    description=(
        "Each entry names the module and function that calls the service, what it does, "
        "and whether it is reachable right now. This is what the stack ribbon on every "
        "page reads from."
    ),
)
async def stack() -> dict[str, object]:
    health = await integration_health()
    return {"ok": True, "data": stack_catalog.stack_report(dict(health))}


# ----------------------------------------------------------------- demo presets

@api.get(
    "/v1/presets",
    tags=["Presets"],
    summary="List the public demo fragments",
    description=(
        "Ten 50-second fragments from the Library of Congress National Screening Room, all "
        "United States public domain. Five are runnable; five are sealed holdouts listed with "
        "their hashes so the set cannot be quietly changed."
    ),
)
async def list_presets(split: Literal["dev", "holdout"] | None = None) -> dict[str, object]:
    return {
        "ok": True,
        "data": {
            "corpus": preset_catalog.corpus_summary(),
            "presets": preset_catalog.list_presets(split=split),
        },
    }


@api.get("/v1/presets/{case_id}", tags=["Presets"], summary="One demo fragment")
async def get_preset(case_id: str) -> dict[str, object]:
    for record in preset_catalog.list_presets():
        if record["case_id"] == case_id:
            return {"ok": True, "data": record}
    raise HTTPException(
        status_code=404,
        detail={
            "code": "preset_not_found",
            "message": f"No demo fragment {case_id!r}.",
            "fix": "GET /v1/presets to list them.",
        },
    )


@api.get(
    "/v1/presets/{case_id}/media",
    tags=["Presets"],
    summary="Watch or download a demo fragment",
    description=(
        "Serves the exact bytes whose SHA-256 is published in the manifest, with range "
        "requests supported so it can be scrubbed in a browser. Add `?download=1` for a "
        "file download. Held-out fragments return 423."
    ),
    response_class=FileResponse,
)
async def preset_media(case_id: str, download: bool = False) -> FileResponse:
    item = preset_catalog.get_preset(case_id)
    if item is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "preset_not_found",
                "message": f"No demo fragment {case_id!r}.",
                "fix": "GET /v1/presets to list them.",
            },
        )
    if item["split"] != "dev":
        raise HTTPException(
            status_code=423,
            detail={
                "code": "holdout_sealed",
                "message": (
                    "Held-out fragments are not served. Publishing them would let the set be "
                    "tuned against, which is the one thing a holdout exists to prevent."
                ),
                "fix": "Use a development case (D01-D05).",
            },
        )
    path = preset_catalog.preset_media_path(case_id)
    if path is None or not path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "code": "media_missing",
                "message": "The fragment file is not present in this deployment.",
                "fix": "Rebuild the image with the eval corpus included.",
            },
        )
    return FileResponse(
        path,
        media_type=item["media_type"],
        filename=f"last-seen-alive_{case_id}.mp4" if download else None,
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Fragment-SHA256": item["sha256"],
            "X-Credit": preset_catalog.LOC_CREDIT,
        },
    )


# -------------------------------------------------------------------- evaluation

@api.get(
    "/v1/example/dossier",
    tags=["Presets"],
    summary="A worked example of an investigation dossier",
    description=(
        "Returns a complete dossier in the exact shape a real investigation returns, so the "
        "output can be read and integrated against before a live run is possible. "
        "**This is not a real investigation.** The fragment is invented, the candidate film does "
        "not exist, and every source is an RFC 2606 reserved domain that can never resolve. It is "
        "built by the same evidence builder and the same deterministic gate that serve a live run, "
        "so the schema and every threshold are genuinely computed, so the example cannot drift away "
        "from what the software actually does. `meta.example` and `data.example` are both `true`."
    ),
)
async def example_dossier() -> dict[str, object]:
    from app.example_dossier import DISCLAIMER, worked_example

    result = worked_example()
    gate = result["gate"]
    return {
        "ok": True,
        "data": result,
        "meta": {
            "example": True,
            "disclaimer": DISCLAIMER,
            "verdict": gate["verdict"],
            "gate": gate,
            "requires_human": True,
            "latency_ms": result.get("latency_ms"),
            "parallel_surfaces_used": result["parallel_retrieval"]["surfaces_used"],
        },
    }


@api.get(
    "/v1/eval/ablation",
    tags=["Evaluation"],
    summary="Control-arm result: what Gemini alone does with the same fragments",
    description=(
        "A measured baseline. The same five development fragments given to Gemini with no web "
        "access, no citation checking and no gate, three samples each. "
        "It contradicted the assumption it was built to test: the model declined to name a film "
        "on both fragments whose evidence cannot support one, so false-confident identifications "
        "were zero. What it did instead was return a different title on each repeat, every one at "
        "high confidence and none with a citable source. See docs/ABLATION.md."
    ),
)
async def evaluation_ablation() -> dict[str, object]:
    report = EVAL_DIR / "reports" / "ablation-control.json"
    if not report.exists():
        return {
            "ok": True,
            "data": {
                "status": "not_run",
                "reason": "Run scripts/run_ablation.py --write to produce it.",
            },
        }
    return {"ok": True, "data": json.loads(report.read_text(encoding="utf-8"))}


@api.get(
    "/v1/standards",
    tags=["Evaluation"],
    summary="Conformance to published archival cataloguing standards",
    description=(
        "Seven requirements quoted from the FIAF Moving Image Cataloguing Manual and EN 15907, "
        "each with the page it comes from, how this system meets it, and the tests that check "
        "it. Five conform, two only partially, and one was failing until the exercise ran. "
        "No archivist has reviewed this system; conformance testing is weaker evidence than a "
        "practitioner review and is not offered as a substitute."
    ),
)
async def standards() -> dict[str, object]:
    return {"ok": True, "data": standards_catalog.conformance_report()}


@api.get(
    "/v1/eval/stability",
    tags=["Evaluation"],
    summary="How stable the verdict is when the input does not change",
    description=(
        "The Arm C figures are a single pass. A second pass over the same five fragments "
        "disagreed with it on four of five verdicts and reproduced neither of its two correct "
        "identities. This reports every pass ever run on the development split, including the "
        "bad ones, so that a single flattering sample cannot be mistaken for a measurement. "
        "The property that did hold across every run: `probable` was never reached, because "
        "that threshold requires a human the API cannot supply."
    ),
)
async def evaluation_stability() -> dict[str, object]:
    report = EVAL_DIR / "reports" / "stability.json"
    if not report.exists():
        raise HTTPException(
            status_code=503,
            detail={
                "code": "stability_not_measured",
                "message": "No stability study has been run for this deployment.",
                "fix": "Run scripts/run_stability.py --write and redeploy.",
            },
        )
    return {"ok": True, "data": json.loads(report.read_text(encoding="utf-8"))}


@api.get(
    "/v1/eval/fix-comparison",
    tags=["Evaluation"],
    summary="What changed when the two defects found by the stability study were fixed",
    description=(
        "The stability study found two defects: candidates that were not films, and "
        "hypotheses nothing ever opposed. Both were fixed. This reports the runs before and "
        "after, scored by the same scorer. One defect is gone; the other is not, and the "
        "second result is the more interesting one -- constraining the candidate type turned "
        "disguised failures into visible wrong answers rather than removing them. Sample "
        "sizes are small and the report says so."
    ),
)
async def evaluation_fix_comparison() -> dict[str, object]:
    report = EVAL_DIR / "reports" / "fix-comparison.json"
    if not report.exists():
        raise HTTPException(
            status_code=503,
            detail={
                "code": "comparison_not_measured",
                "message": "No before/after comparison has been run for this deployment.",
                "fix": "Run scripts/compare_fix.py --write and redeploy.",
            },
        )
    return {"ok": True, "data": json.loads(report.read_text(encoding="utf-8"))}


@api.get(
    "/v1/practice",
    tags=["Evaluation"],
    summary="Published practitioner objections, and how this system answers them",
    description=(
        "No archivist has reviewed this project. This is the nearest honest substitute: "
        "demands made in peer-reviewed studies of AI cataloguing, in the FIAF manual, and in "
        "the Library of Congress's own account of how it identifies unidentified film -- each "
        "quoted verbatim, cited, and paired with the mechanism here that answers it. Four "
        "entries are unanswered or only partly answered, including the missing archivist "
        "review itself. Nobody cited has seen this system or endorses it."
    ),
)
async def practice() -> dict[str, object]:
    return {"ok": True, "data": practice_register.register()}


@api.get(
    "/v1/dossiers",
    tags=["Evaluation"],
    summary="Complete dossiers from real runs on the development split",
    description=(
        "The full output of an investigation takes minutes to produce. These are captured "
        "from real runs of this deployed service against the public demo fragments, "
        "unedited, so the product can be read without waiting for one. Held-out cases are "
        "never included."
    ),
)
async def dossiers() -> dict[str, object]:
    index = DOSSIER_DIR / "index.json"
    if not index.exists():
        raise HTTPException(
            status_code=503,
            detail={
                "code": "dossiers_not_captured",
                "message": "No dossiers have been captured for this deployment.",
                "fix": "Run scripts/capture_dossiers.py and redeploy.",
            },
        )
    return {"ok": True, "data": json.loads(index.read_text(encoding="utf-8"))}


@api.get(
    "/v1/dossiers/{case_id}",
    tags=["Evaluation"],
    summary="One complete captured dossier",
    description=(
        "The entire response from a real run, including every claim, every citation, which "
        "citations survived the live audit, and the seven gate thresholds."
    ),
)
async def dossier(case_id: str) -> dict[str, object]:
    path = DOSSIER_DIR / f"{case_id.upper()}.json"
    if not path.is_file() or path.parent != DOSSIER_DIR:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "dossier_not_found",
                "message": "No captured dossier for that case.",
                "fix": "GET /v1/dossiers to list what has been captured.",
            },
        )
    return {"ok": True, "data": json.loads(path.read_text(encoding="utf-8"))}


@api.get(
    "/v1/census/{findall_id}",
    tags=["Investigate"],
    summary="Collect a named-catalogue census",
    description=(
        "An investigation commissions a Parallel FindAll census of the archives whose own "
        "catalogues list the leading candidate. That genuinely takes minutes to an hour, so the "
        "dossier does not block on it: it returns a handle and you collect the result here. "
        "Poll until `status` is no longer active."
    ),
)
async def collect_census(findall_id: str, _key: ApiKeyRecord = Depends(require_key)) -> dict[str, object]:
    _partner_required()
    from app.partners.parallel_research import collect_named_catalogue_census

    try:
        report = await asyncio.to_thread(collect_named_catalogue_census, findall_id)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "census_unavailable",
                "message": f"The census could not be collected ({type(exc).__name__}).",
                "fix": "Check the findall_id from the investigation response and retry.",
            },
        ) from exc
    return {"ok": True, "data": report}


@api.get(
    "/v1/eval/arm-c",
    tags=["Evaluation"],
    summary="Full-system result on the development split",
    description=(
        "The third arm of the ablation, run once the Parallel credential was attached. Same "
        "five development fragments, all six Parallel surfaces live. Two of three identifiable "
        "cases were surfaced correctly against the sealed answer key, with zero false-confident "
        "identifications and one honest miss. The held-out split is untouched."
    ),
)
async def evaluation_arm_c() -> dict[str, object]:
    report = EVAL_DIR / "reports" / "arm-c-development.json"
    if not report.exists():
        return {"ok": True, "data": {"status": "not_run"}}
    return {"ok": True, "data": json.loads(report.read_text(encoding="utf-8"))}


@api.get("/v1/eval/corpus", tags=["Evaluation"], summary="Benchmark corpus state")
async def evaluation_corpus() -> dict[str, object]:
    return preset_catalog.corpus_summary()


@api.get(
    "/v1/eval/manifest",
    tags=["Evaluation"],
    summary="Download the full public manifest",
    description=(
        "The unedited manifest, including each case's selection rationale, transforms and "
        "SHA-256. The site's own descriptions are written to avoid quoting the discriminating "
        "evidence; this file does not hold back."
    ),
)
async def evaluation_manifest() -> JSONResponse:
    payload = json.loads((EVAL_DIR / "manifest.json").read_text(encoding="utf-8-sig"))
    return JSONResponse(
        payload,
        headers={"Content-Disposition": 'attachment; filename="last-seen-alive-manifest.json"'},
    )


# ----------------------------------------------------------------- investigation

def _partner_required() -> None:
    if not parallel_client.is_configured():
        raise HTTPException(
            status_code=503,
            detail={
                "code": "partner_credential_not_configured",
                "message": (
                    "Parallel is the only open-web path in this product. Without it the "
                    "workflow stops rather than answering from model memory."
                ),
                "fix": "Attach the Parallel credential and retry; see GET /health/integrations.",
            },
        )


def _response(result: dict[str, Any], request: Request) -> dict[str, object]:
    gate = result["gate"]
    return {
        "ok": True,
        "data": result,
        "meta": {
            "verdict": gate["verdict"],
            "gate": gate,
            "requires_human": True,
            "latency_ms": result.get("latency_ms"),
            "parallel_surfaces_used": result.get("parallel_retrieval", {}).get("surfaces_used", []),
            "usage": getattr(request.state, "usage", None),
        },
    }


@api.post(
    "/v1/identify",
    tags=["Investigate"],
    summary="Investigate a public demo fragment",
    description=(
        "Runs the full five-role workflow on one of the runnable presets. An abstention is "
        "a correct outcome and returns 200 with `meta.verdict = \"abstain\"`."
    ),
)
async def identify(
    request: IdentifyRequest, http_request: Request, _key: ApiKeyRecord = Depends(require_key)
) -> dict[str, object]:
    item = preset_catalog.get_preset(request.sample_id)
    if item is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "sample_not_found",
                "message": "Unknown evaluation sample.",
                "fix": "GET /v1/presets to list runnable cases.",
            },
        )
    if item["split"] != "dev":
        raise HTTPException(
            status_code=423,
            detail={
                "code": "holdout_sealed",
                "message": "Held-out fragments remain sealed until the workflow is frozen and tagged.",
                "fix": "Run a development case (D01-D05).",
            },
        )
    _partner_required()

    from app.adk_runtime import InvestigationNotConfigured, run_investigation

    try:
        result = await run_investigation(
            fragment=(EVAL_DIR / item["file"]).read_bytes(),
            media_type=item["media_type"],
            provided_label=item.get("provided_label"),
            origin=f"preset:{request.sample_id}",
            sample_id=request.sample_id,
            depth=request.depth,
        )
    except InvestigationNotConfigured as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "runtime_not_configured",
                "message": str(exc),
                "fix": "Set the missing runtime configuration and redeploy.",
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "live_investigation_failed",
                "message": (
                    f"The live workflow failed closed ({type(exc).__name__}). No verdict was "
                    "fabricated."
                ),
                "fix": "Retry; if it persists, check GET /health/integrations.",
            },
        ) from exc
    return _response(result, http_request)


@api.post(
    "/v1/investigate",
    tags=["Investigate"],
    summary="Investigate your own fragment",
    description=(
        "Upload a short excerpt of an unidentified fragment (video or a single frame) and get "
        "the same dossier the presets produce.\n\n"
        "The file is held in memory for the length of the request and is never written to disk, "
        "logged, or used to train anything. Excerpts of it do travel to Google Cloud (Gemini "
        "reads the frames) and text drawn from it travels to Parallel as search queries. That "
        "is what the investigation is. Do not upload material you are not free to send to those "
        "two services.\n\n"
        "Limits: 48 MB, and one of mp4, mov, webm, mkv, jpeg, png, webp."
    ),
)
async def investigate(
    http_request: Request,
    fragment: UploadFile = File(
        ..., description="The fragment. A 30-60 second excerpt works best."
    ),
    provided_label: str | None = Form(
        default=None,
        max_length=160,
        description=(
            "Any title your catalogue currently carries for this material, if it has one. "
            "Supplying it lets the workflow try to contradict it rather than inherit it. "
            "A catalogue title, not instructions: this text reaches the model, and it is "
            "capped and quoted rather than trusted."
        ),
    ),
    depth: Literal["standard", "deep"] = Form(default="standard"),
    _key: ApiKeyRecord = Depends(require_key),
) -> dict[str, object]:
    from app.adk_runtime import (
        MAX_UPLOAD_BYTES,
        FragmentRejected,
        InvestigationNotConfigured,
        run_investigation,
        validate_fragment,
    )

    # Judge the caller's own request before reporting on our dependencies. Telling
    # someone who uploaded a .zip that Parallel is unavailable sends them looking
    # for a problem on our side that has nothing to do with why their call failed.
    data = await fragment.read(MAX_UPLOAD_BYTES + 1)
    media_type = (fragment.content_type or "").split(";")[0].strip().lower()
    try:
        validate_fragment(data=data, media_type=media_type)
    except FragmentRejected as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "fragment_rejected",
                "message": str(exc),
                "fix": "Send a short excerpt in a supported format.",
            },
        ) from exc

    _partner_required()
    label = (provided_label or "").strip() or None
    try:
        result = await run_investigation(
            fragment=data,
            media_type=media_type,
            provided_label=label,
            origin="upload",
            sample_id=None,
            depth=depth,
        )
    except InvestigationNotConfigured as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "runtime_not_configured", "message": str(exc), "fix": "Redeploy with the missing configuration."},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "live_investigation_failed",
                "message": (
                    f"The live workflow failed closed ({type(exc).__name__}). No verdict was "
                    "fabricated and your file was discarded."
                ),
                "fix": "Retry with a shorter excerpt; check GET /health/integrations.",
            },
        ) from exc
    finally:
        await fragment.close()
    return _response(result, http_request)


@api.post(
    "/v1/watch",
    tags=["Investigate"],
    summary="Leave a standing watch on an unidentified fragment",
    description=(
        "Registers a Parallel Monitor on the verbatim strings visible in a fragment the "
        "evidence could not identify. An abstention is the right answer today and the wrong "
        "answer forever; archives digitise continuously. This is how the fragment gets "
        "looked at again."
    ),
)
async def watch(
    request: WatchRequest, _key: ApiKeyRecord = Depends(require_key)
) -> dict[str, object]:
    _partner_required()
    from app.partners.parallel_verify import open_cold_case_monitor

    try:
        report = await asyncio.to_thread(
            open_cold_case_monitor,
            fragment_label=request.fragment_label,
            rare_strings=request.rare_strings,
            frequency=request.frequency,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "monitor_not_created",
                "message": f"The watch could not be created ({type(exc).__name__}).",
                "fix": "Retry; check GET /health/integrations.",
            },
        ) from exc
    return {"ok": True, "data": report}


api.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
app = api
