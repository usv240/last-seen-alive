"""The dossier archive and the practice register, as served.

Both exist to answer a criticism of the product rather than to add a feature.
The archive exists because a full run takes minutes, so the only way to see what
this product produces was to wait for it -- which meant most readers never saw
the output at all. The register exists because "no archivist has reviewed this"
was a sentence in a limitations file rather than a surface anyone would find.

The tests worth writing are therefore about honesty rather than plumbing: that a
held-out case can never be published as a dossier, that the archive refuses
clearly rather than 500-ing when nothing has been captured, and that a captured
dossier still carries the disclaimers the live path attaches.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.api.main import DOSSIER_DIR, app


@pytest.fixture(scope="module")
def api() -> TestClient:
    with TestClient(app) as client:
        yield client


# ---------------------------------------------------------------- the pages

@pytest.mark.parametrize("path", ["/dossiers", "/practice"])
def test_the_new_pages_are_served(api: TestClient, path: str) -> None:
    response = api.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


@pytest.mark.parametrize(
    "page", ["index.html", "presets.html", "api.html", "stack.html",
             "dossiers.html", "practice.html"]
)
def test_every_page_links_to_every_other_page(page: str) -> None:
    """A page nothing links to is a page nobody finds."""
    from app.api.main import WEB_DIR

    html = (WEB_DIR / page).read_text(encoding="utf-8")
    for destination in ('href="/"', 'href="/presets"', 'href="/dossiers"',
                        'href="/practice"', 'href="/api"', 'href="/stack"'):
        assert destination in html, f"{page} does not link to {destination}"


# ------------------------------------------------------------ the register

def test_practice_register_is_served_with_its_unmet_entries(api: TestClient) -> None:
    payload = api.get("/v1/practice").json()
    assert payload["ok"] is True
    data = payload["data"]

    assert data["tally"]["not_met"] >= 1, "the register must publish what it does not do"
    assert "Nobody cited endorses this system" in data["disclaimer"]

    ids = {entry["id"] for entry in data["entries"]}
    assert "P5" in ids
    missing_review = next(e for e in data["entries"] if e["id"] == "P5")
    assert missing_review["status"] == "not_met"
    assert missing_review["source"]["url"].startswith("https://")


def test_every_register_entry_reaches_a_real_source(api: TestClient) -> None:
    data = api.get("/v1/practice").json()["data"]
    for entry in data["entries"]:
        assert entry["source"]["citation"], f"{entry['id']} lost its citation in serialisation"
        assert entry["quote"], f"{entry['id']} lost its quote in serialisation"


# ------------------------------------------------------------- the archive

def test_the_archive_refuses_clearly_when_nothing_is_captured(
    api: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """A deployment without captures must say so, not fail obscurely."""
    monkeypatch.setattr("app.api.main.DOSSIER_DIR", tmp_path)
    response = api.get("/v1/dossiers")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "dossiers_not_captured"


def test_an_unknown_case_is_a_clean_404(api: TestClient) -> None:
    response = api.get("/v1/dossiers/ZZ9")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "dossier_not_found"


@pytest.mark.skipif(
    not (DOSSIER_DIR / "index.json").exists(), reason="no dossiers captured in this checkout"
)
class TestCapturedDossiers:
    def test_the_index_lists_only_development_cases(self, api: TestClient) -> None:
        """Publishing a held-out dossier would burn the one unrepeatable measurement."""
        data = api.get("/v1/dossiers").json()["data"]
        assert data["split"] == "dev"
        for row in data["dossiers"]:
            assert row["case_id"].startswith("D"), f"{row['case_id']} is not a development case"

    def test_no_held_out_case_was_ever_written_to_disk(self) -> None:
        for path in DOSSIER_DIR.glob("*.json"):
            assert not path.stem.startswith("H"), f"a held-out dossier exists on disk: {path.name}"

    def test_each_dossier_carries_its_capture_provenance(self, api: TestClient) -> None:
        rows = api.get("/v1/dossiers").json()["data"]["dossiers"]
        for row in rows:
            data = api.get(f"/v1/dossiers/{row['case_id']}").json()["data"]
            captured = data["captured"]
            assert captured["service"].startswith("https://")
            assert captured["elapsed_seconds"] > 0
            assert "not edited" in captured["note"].lower()

    def test_each_dossier_still_carries_its_gate(self, api: TestClient) -> None:
        """A captured dossier is the whole response, not a cleaned-up summary."""
        rows = api.get("/v1/dossiers").json()["data"]["dossiers"]
        for row in rows:
            meta = api.get(f"/v1/dossiers/{row['case_id']}").json()["data"]["meta"]
            assert meta["verdict"] in {"probable", "candidates", "abstain", "contradict"}
            assert "human_approved" in meta["gate"]["thresholds"]

    def test_no_captured_dossier_claims_a_probable_identity(self, api: TestClient) -> None:
        """`probable` needs a human. Nothing captured through the API can have one."""
        rows = api.get("/v1/dossiers").json()["data"]["dossiers"]
        for row in rows:
            assert row["verdict"] != "probable", (
                f"{row['case_id']} reached probable without an archivist, which the gate forbids"
            )

    def test_the_index_agrees_with_the_dossiers_it_indexes(self, api: TestClient) -> None:
        for row in api.get("/v1/dossiers").json()["data"]["dossiers"]:
            stored = json.loads((DOSSIER_DIR / f"{row['case_id']}.json").read_text(encoding="utf-8"))
            assert stored["meta"]["verdict"] == row["verdict"]
