"""The practitioner objection register has to be executable, not decorative.

app/practice.py answers demands made in published archival sources. A register
like that is worthless if it is only prose: the natural failure mode is that a
mechanism gets refactored away, the claim about it stays on the website, and the
project ends up asserting a safeguard it no longer has. That is precisely the
kind of unsourced confidence this whole project exists to argue against.

So each structural promise is checked here, and the two load-bearing behavioural
claims -- P1 (human approval is unreachable through the API) and P7 (an unsourced
claim cannot carry a threshold) -- are executed against the real gate rather than
described.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_identity_gate import complete_context, sourced_claim

from app.gates import IdentityGate
from app.practice import REGISTER, SOURCES, register, unmet

ROOT = Path(__file__).resolve().parents[1]


# ------------------------------------------------------------------ structure

def test_every_entry_cites_a_source_that_exists() -> None:
    for entry in REGISTER:
        assert entry["source"] in SOURCES, f"{entry['id']} cites unknown source {entry['source']}"


def test_every_source_carries_a_citation_and_a_url() -> None:
    for key, source in SOURCES.items():
        assert source["citation"].strip(), f"{key} has no citation"
        assert source["url"].startswith("https://"), f"{key} has no resolvable URL"
        assert source["kind"] in {
            "peer_reviewed_study", "professional_standard", "national_archive_practice"
        }, f"{key} has an unrecognised kind"


def test_every_quote_is_substantial() -> None:
    """A three-word fragment can be made to mean anything. Quotes carry context."""
    for entry in REGISTER:
        assert len(entry["quote"].split()) >= 6, f"{entry['id']} quotes too little to be fair"


@pytest.mark.parametrize("entry", REGISTER, ids=lambda e: e["id"])
def test_every_cited_repository_file_exists(entry: dict) -> None:
    """The register names mechanisms. A named mechanism that is gone is a false claim."""
    for item in entry["evidence"]:
        if item.startswith("/"):
            continue  # an endpoint, checked separately against the live app
        assert (ROOT / item).exists(), f"{entry['id']} cites {item}, which does not exist"


def test_every_cited_endpoint_is_served() -> None:
    from fastapi.testclient import TestClient

    from app.api.main import app

    referenced = {
        item for entry in REGISTER for item in entry["evidence"] if item.startswith("/")
    }
    with TestClient(app) as client:
        served = set(client.get("/openapi.json").json()["paths"])
    missing = referenced - served
    assert not missing, f"the register cites endpoints the API does not serve: {sorted(missing)}"


# -------------------------------------------------------------------- honesty

def test_the_register_admits_something_it_does_not_do() -> None:
    """A register in which every objection is answered is a brochure."""
    assert unmet(), "no unmet objection: either the register is dishonest or it is incomplete"


def test_unmet_entries_say_what_would_close_them() -> None:
    for entry in unmet():
        assert entry.get("what_would_close_it", "").strip(), (
            f"{entry['id']} is unmet but does not say what would close it"
        )


def test_the_missing_archivist_review_is_named_as_unmet() -> None:
    """The central limitation must never quietly become 'met'."""
    review = next(entry for entry in REGISTER if entry["id"] == "P5")
    assert review["status"] == "not_met"
    assert "No archivist has reviewed" in review["how_this_system_answers"]


#: Phrases that would claim a practitioner blessed this project. Each is only a
#: problem when asserted; "No archivist has reviewed this system" is the opposite
#: of a claim, and P5 exists to say exactly that.
ENDORSEMENT_PHRASES = ("endorses this", "endorsed by", "approved by", "reviewed this system")
DENIALS = ("no archivist", "has not", "have not", "never", "cannot obtain", "not yet")


def test_no_entry_claims_an_endorsement() -> None:
    """Citing someone is not being endorsed by them."""
    payload = register()
    assert "Nobody cited endorses this system" in payload["disclaimer"]
    for entry in REGISTER:
        for sentence in (entry["how_this_system_answers"] + " " + entry["demand"]).split("."):
            lowered = sentence.lower()
            if any(denial in lowered for denial in DENIALS):
                continue
            for forbidden in ENDORSEMENT_PHRASES:
                assert forbidden not in lowered, (
                    f"{entry['id']} implies an endorsement it does not have: {sentence.strip()!r}"
                )


def test_the_tally_matches_the_entries() -> None:
    payload = register()
    assert payload["total"] == len(REGISTER)
    assert sum(payload["tally"].values()) == len(REGISTER)


# --------------------------------------------------------------- behavioural

def test_p1_human_approval_really_is_load_bearing() -> None:
    """P1 claims `probable` is unreachable without a human. Prove it on the real gate."""
    claims = [sourced_claim(f"archive{i}.example.org") for i in range(3)]
    context = complete_context(claims)

    approved = IdentityGate().evaluate(claims, {**context, "human_approved": True})
    assert approved.verdict == "probable", (
        "the fixture must otherwise reach probable, or this test proves nothing"
    )

    withheld = IdentityGate().evaluate(claims, {**context, "human_approved": False})
    assert withheld.verdict != "probable", "P1 is false: probable was reached without a human"
    assert withheld.thresholds["human_approved"] is False
    assert withheld.requires_human is True


def test_p7_an_unsourced_claim_cannot_carry_a_threshold() -> None:
    """P7 quotes FIAF: information in a record must be derived from a source."""
    from agentic_core.evidence import Claim, stable_claim_id

    unsourced = Claim(
        claim_id=stable_claim_id("film-42", "matches", "nowhere"),
        claim_text="The fragment is the 1919 comedy.",
        subject="film-42",
        agent_id="phrase-hunter",
        stance="supports",
        sources=(),
        confidence_basis="Recalled, not retrieved.",
    )
    assert unsourced.is_decisive_eligible is False, (
        "P7 is false: a claim with no source was treated as decisive"
    )

    context = complete_context([unsourced])
    result = IdentityGate().evaluate([unsourced], context)
    assert result.verdict != "probable", "P7 is false: an unsourced claim reached probable"
