from datetime import UTC, datetime

from agentic_core.evidence import Claim, Source, stable_claim_id
from agentic_core.gate import Candidate
from app.gates import IdentityGate, assert_permitted_holdings_language


def sourced_claim(domain: str, *, subject: str = "film-42") -> Claim:
    claim_id = stable_claim_id(subject, "matches", domain)
    return Claim(
        claim_id=claim_id,
        claim_text=f"Evidence from {domain} supports the candidate.",
        subject=subject,
        agent_id="phrase-hunter",
        stance="supports",
        sources=(
            Source(
                url=f"https://{domain}/record",
                domain=domain,
                excerpt="A rare intertitle phrase appears in the 1917 review.",
                retrieved_at=datetime(2026, 8, 20, tzinfo=UTC),
                verified=True,
            ),
        ),
        confidence_basis="The verified excerpt contains the exact rare phrase.",
    )


def complete_context(claims: list[Claim]) -> dict[str, object]:
    return {
        "candidates": [
            Candidate(
                candidate_id="film-42",
                label="Example Film",
                score=0.82,
                decisive_claim_ids=tuple(claim.claim_id for claim in claims),
            )
        ],
        "decisive_clue_families": ["intertitle", "performer"],
        "temporal_compatibility": True,
        "entity_compatibility": True,
        "human_approved": True,
    }


def test_probable_requires_every_threshold() -> None:
    claims = [sourced_claim(domain) for domain in ("one.example", "two.example", "three.example")]
    result = IdentityGate().evaluate(claims, complete_context(claims))
    assert result.verdict == "probable"
    assert not result.failed


def test_missing_human_approval_returns_candidates() -> None:
    claims = [sourced_claim(domain) for domain in ("one.example", "two.example", "three.example")]
    context = complete_context(claims)
    context["human_approved"] = False
    result = IdentityGate().evaluate(claims, context)
    assert result.verdict == "candidates"
    assert result.failed == ("human_approved",)


def test_verified_contradiction_blocks_probable_identity() -> None:
    claims = [sourced_claim(domain) for domain in ("one.example", "two.example", "three.example")]
    contradiction = Claim(
        claim_id=stable_claim_id("film-42", "release-year", "incompatible"),
        claim_text="The candidate was released after the observed fragment date.",
        subject="film-42",
        agent_id="skeptic",
        stance="contradicts",
        sources=(
            Source(
                url="https://four.example/release",
                domain="four.example",
                excerpt="The film was released in 1922.",
                verified=True,
            ),
        ),
        confidence_basis="The verified release record conflicts with the observed edge code.",
    )
    result = IdentityGate().evaluate([*claims, contradiction], complete_context(claims))
    assert result.verdict == "candidates"
    assert "unresolved_contradictions==0" in result.failed


def test_holdings_language_linter_rejects_absolute_claims() -> None:
    for text in ("This is the last copy.", "The only surviving reel was found.", "A sole print."):
        try:
            assert_permitted_holdings_language(text)
        except ValueError:
            pass
        else:
            raise AssertionError(f"forbidden wording passed: {text}")
    permitted = "No additional holding was found across FIAF and AFI as of 20 August 2026."
    assert assert_permitted_holdings_language(permitted) == permitted

