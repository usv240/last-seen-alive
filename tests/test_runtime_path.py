from pathlib import Path

from fastapi.testclient import TestClient

from app.adk_runtime import run_development_investigation
from app.api.main import api


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
    monkeypatch.setattr("app.adk_runtime.run_development_investigation", fake_run)
    response = TestClient(api).post("/v1/identify", json={"sample_id": "D01"})
    assert response.status_code == 200
    assert response.json()["meta"]["verdict"] == "abstain"
    assert captured["sample_id"] == "D01"
    assert Path(captured["fragment_path"]).name == "fragment_D01.mp4"


def test_holdout_remains_sealed_even_when_partner_is_configured(monkeypatch):
    monkeypatch.setenv("PARALLEL_API_KEY", "test-only")
    response = TestClient(api).post("/v1/identify", json={"sample_id": "H01"})
    assert response.status_code == 423
    assert response.json()["error"]["code"] == "holdout_sealed"


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
