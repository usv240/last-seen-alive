
import pytest
from fastapi.testclient import TestClient

from agentic_core.api.keys import mint_key
from app.adk_runtime import FragmentRejected, run_development_investigation, validate_fragment
from app.api.main import api, pepper


def auth() -> dict[str, str]:
    key, _ = mint_key(tier="judge", pepper=pepper.encode("utf-8"))
    return {"Authorization": f"Bearer {key}"}


def test_development_sample_uses_live_runtime_when_partner_is_configured(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_run(**kwargs):
        captured.update(kwargs)
        return {
            "status": "completed",
            "gate": {"verdict": "abstain", "passed": [], "failed": ["human_approved"]},
            "requires_human": True,
        }

    monkeypatch.setenv("PARALLEL_API_KEY", "test-only")
    monkeypatch.setattr("app.adk_runtime.run_investigation", fake_run)
    response = TestClient(api).post(
        "/v1/identify", json={"sample_id": "D01"}, headers=auth()
    )
    assert response.status_code == 200
    assert response.json()["meta"]["verdict"] == "abstain"
    assert captured["sample_id"] == "D01"
    assert captured["origin"] == "preset:D01"
    assert isinstance(captured["fragment"], bytes) and captured["fragment"]


def test_identify_requires_an_api_key(monkeypatch):
    monkeypatch.setenv("PARALLEL_API_KEY", "test-only")
    response = TestClient(api).post("/v1/identify", json={"sample_id": "D01"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "missing_api_key"


def test_holdout_remains_sealed_even_when_partner_is_configured(monkeypatch):
    monkeypatch.setenv("PARALLEL_API_KEY", "test-only")
    response = TestClient(api).post(
        "/v1/identify", json={"sample_id": "H01"}, headers=auth()
    )
    assert response.status_code == 423
    assert response.json()["error"]["code"] == "holdout_sealed"


def test_holdout_media_is_never_served():
    response = TestClient(api).get("/v1/presets/H01/media")
    assert response.status_code == 423
    assert response.json()["error"]["code"] == "holdout_sealed"


def test_development_media_is_watchable_and_downloadable():
    client = TestClient(api)
    watch = client.get("/v1/presets/D01/media")
    assert watch.status_code == 200
    assert watch.headers["content-type"].startswith("video/")
    assert "Library of Congress" in watch.headers["x-credit"]
    assert watch.headers["accept-ranges"] == "bytes"

    download = client.get("/v1/presets/D01/media?download=1")
    assert "attachment" in download.headers.get("content-disposition", "")


def test_media_bytes_match_the_published_hash():
    """The published SHA-256 has to be the file we actually serve, or it is decoration."""
    import hashlib

    from app import presets as catalog

    item = catalog.get_preset("D01")
    body = TestClient(api).get("/v1/presets/D01/media").content
    assert hashlib.sha256(body).hexdigest() == item["sha256"]


def test_preset_listing_does_not_leak_the_discriminating_evidence():
    """The site's own copy must not quote the clue the workflow is meant to find.

    D02's manifest entry contains the verbatim intertitle. If that text reached
    the public preset listing, a viewer could read the answer off the page and
    then watch the agent 'discover' it.
    """
    payload = TestClient(api).get("/v1/presets").json()["data"]
    blob = str(payload).lower()
    assert "jiminy" not in blob
    assert "bray studios" not in blob
    for record in payload["presets"]:
        assert record["credit"].startswith("Library of Congress")


def test_uploaded_fragment_is_validated_before_any_partner_call():
    with pytest.raises(FragmentRejected, match="empty"):
        validate_fragment(data=b"", media_type="video/mp4")
    with pytest.raises(FragmentRejected, match="Unsupported media type"):
        validate_fragment(data=b"x" * 10, media_type="application/zip")
    with pytest.raises(FragmentRejected, match="limit"):
        validate_fragment(data=b"x" * (48 * 1024 * 1024 + 1), media_type="video/mp4")
    validate_fragment(data=b"x" * 10, media_type="video/mp4")


def test_runtime_rejects_holdout_before_reading_media(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "location")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("PARALLEL_API_KEY", "test-only")
    missing = tmp_path / "never-read.mp4"
    try:
        import asyncio

        asyncio.run(
            run_development_investigation(
                sample_id="H99",
                fragment_path=missing,
                media_type="video/mp4",
                provided_label=None,
            )
        )
    except PermissionError as exc:
        assert "development" in str(exc)
    else:
        raise AssertionError("held-out input was not rejected")


def test_stack_endpoint_names_every_sponsor_surface():
    data = TestClient(api).get("/v1/stack").json()["data"]
    parallel = {entry["key"] for entry in data["parallel"]}
    assert parallel == {
        "parallel_search",
        "parallel_task",
        "parallel_extract",
        "parallel_findall",
        "parallel_task_group",
        "parallel_monitor",
    }
    assert len(data["google_cloud"]) == 5
    for entry in data["google_cloud"] + data["parallel"]:
        assert entry["call_site"], f"{entry['key']} does not name its call site"
        assert entry["status"] in {"live", "unavailable", "unknown"}


def test_upload_validation_reports_the_users_error_not_ours(monkeypatch):
    """A bad upload must not be blamed on a missing partner credential.

    Reporting "Parallel is unavailable" to someone who sent a .zip sends them
    looking for a problem on our side that has nothing to do with why their
    call failed.
    """
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
    response = TestClient(api).post(
        "/v1/investigate",
        headers=auth(),
        files={"fragment": ("x.zip", b"not a video", "application/zip")},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "fragment_rejected"


def test_oversized_request_is_refused_before_the_body_is_read():
    """The out-of-memory guard.

    Starlette spools a multipart body past 1 MB to a temp file, and on Cloud Run
    the filesystem is memory-backed — so without a Content-Length check a large
    POST is an out-of-memory button. Nothing is read here: the declared length
    alone is enough to refuse.
    """
    from app.api.main import MAX_REQUEST_BYTES

    response = TestClient(api).post(
        "/v1/investigate",
        headers={**auth(), "content-length": str(MAX_REQUEST_BYTES + 1)},
        content=b"",
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"


def test_a_normal_sized_request_passes_the_body_limit():
    response = TestClient(api).post(
        "/v1/investigate",
        headers=auth(),
        files={"fragment": ("x.zip", b"small", "application/zip")},
    )
    assert response.status_code == 422  # rejected on type, not on size


def test_provided_label_is_capped():
    """The label is interpolated into the model prompt, so it cannot be unbounded."""
    response = TestClient(api).post(
        "/v1/investigate",
        headers=auth(),
        files={"fragment": ("x.mp4", b"\x00" * 64, "video/mp4")},
        data={"provided_label": "A" * 500},
    )
    assert response.status_code == 422


def test_cors_allows_a_browser_client_on_another_origin():
    """The product's pitch is 'integrate this into your catalogue tooling'.

    Every request is authorised by a Bearer token and nothing uses cookies, so
    allowing cross-origin calls opens no CSRF surface.
    """
    response = TestClient(api).options(
        "/v1/presets",
        headers={
            "Origin": "https://an-archive.example.org",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert "authorization" in response.headers["access-control-allow-headers"].lower()
    # No credentials: a cross-origin page can never borrow ambient authority.
    assert "access-control-allow-credentials" not in response.headers
