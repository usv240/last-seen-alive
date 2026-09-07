"""A citation the model invented must not be able to raise the verdict.

The Skeptic and the research agents are instructed to preserve citations, but an
instruction cannot stop a model from emitting a plausible URL it never saw. These
tests hold the enforcement that can: app/evidence_builder.py checks every source
against app/partners/citation_registry.py, which records what the Parallel tools
actually returned during the run.

The property that matters is directional. A fabricated citation may only ever
weaken a candidate -- by leaving its claims undecisive -- and may never satisfy a
gate threshold.
"""

from __future__ import annotations

from app.evidence_builder import build
from app.evidence_schema import (
    CompiledCandidate,
    CompiledClaim,
    CompiledEvidence,
    CompiledSource,
)
from app.gates.identity import IdentityGate
from app.partners.citation_registry import CitationRegistry

REAL_URL = "https://www.loc.gov/item/through-the-breakers"
REAL_EXCERPT = "Through the Breakers was formerly supplied under the title Those Who Pay."


def registry_with_one_real_result() -> CitationRegistry:
    registry = CitationRegistry()
    registry.record_search(
        {
            "provider": "parallel_search_v1",
            "search_id": "srch_test",
            "results": [
                {
                    "url": REAL_URL,
                    "title": "Through the Breakers",
                    "excerpts": [REAL_EXCERPT],
                }
            ],
        }
    )
    return registry


def claim(url: str, excerpt: str, *, stance: str = "supports") -> CompiledClaim:
    return CompiledClaim(
        claim_text="The fragment matches Through the Breakers (1928).",
        subject="through_the_breakers_1928",
        stance=stance,
        clue_family="intertitle_text",
        confidence_basis="Cited catalogue record.",
        sources=[CompiledSource(url=url, excerpt=excerpt)],
    )


def compiled(*claims: CompiledClaim, score: float = 0.9) -> CompiledEvidence:
    return CompiledEvidence(
        candidates=[
            CompiledCandidate(
                candidate_id="through_the_breakers_1928",
                title="Through the Breakers",
                year="1928",
                score=score,
                rationale="Intertitle match.",
            )
        ],
        claims=list(claims),
        temporal_compatibility=True,
        entity_compatibility=True,
    )


def test_url_parallel_never_returned_is_discarded() -> None:
    registry = registry_with_one_real_result()
    built = build(compiled(claim("https://invented.example.com/record", REAL_EXCERPT)), registry)

    assert built.rejected, "a fabricated URL must be recorded as rejected"
    assert built.rejected[0]["reason"] == "not_returned_by_parallel_in_this_run"
    assert built.claims[0].sources == ()
    assert not built.claims[0].is_decisive_eligible
    assert built.candidates[0].decisive_claim_ids == ()


def test_excerpt_not_in_retrieved_text_is_not_decisive() -> None:
    registry = registry_with_one_real_result()
    built = build(compiled(claim(REAL_URL, "A sentence that was never on that page.")), registry)

    assert built.rejected[0]["reason"] == "excerpt_not_found_in_retrieved_text"
    assert built.claims[0].sources[0].verified is False
    assert not built.claims[0].is_decisive_eligible


def test_genuine_citation_survives_and_is_decisive() -> None:
    registry = registry_with_one_real_result()
    built = build(compiled(claim(REAL_URL, REAL_EXCERPT)), registry)

    assert built.rejected == []
    assert built.claims[0].sources[0].verified is True
    assert built.claims[0].is_decisive_eligible
    assert built.candidates[0].decisive_claim_ids == (built.claims[0].claim_id,)
    assert built.clue_families == {"intertitle_text"}


def test_fabricated_citations_cannot_pass_the_identity_gate() -> None:
    """The whole point: invented sources must not reach a probable identity."""
    registry = registry_with_one_real_result()
    built = build(
        compiled(
            claim("https://invented-one.example.com/a", "Invented supporting text."),
            claim("https://invented-two.example.com/b", "More invented supporting text."),
            claim("https://invented-three.example.com/c", "Still invented."),
        ),
        registry,
    )
    result = IdentityGate().evaluate(built.claims, built.gate_context(human_approved=True))

    assert result.verdict != "probable"
    assert result.thresholds["independent_source_domains>=3"] is False
    assert result.thresholds["distinct_clue_families>=2"] is False
    assert len(built.rejected) == 3


def test_contradiction_from_the_skeptic_blocks_a_probable_identity() -> None:
    registry = registry_with_one_real_result()
    registry.record_search(
        {
            "provider": "parallel_search_v1",
            "search_id": "srch_contra",
            "results": [
                {
                    "url": "https://catalogue.bfi.org.uk/record/9911",
                    "title": "BFI record",
                    "excerpts": ["The production was released in 1931, not 1928."],
                }
            ],
        }
    )
    contradiction = CompiledClaim(
        claim_text="The release year is 1931, which is incompatible with the candidate.",
        subject="through_the_breakers_1928",
        stance="contradicts",
        clue_family="release_date",
        confidence_basis="Cited catalogue record.",
        sources=[
            CompiledSource(
                url="https://catalogue.bfi.org.uk/record/9911",
                excerpt="The production was released in 1931, not 1928.",
            )
        ],
    )
    built = build(compiled(claim(REAL_URL, REAL_EXCERPT), contradiction), registry)
    result = IdentityGate().evaluate(built.claims, built.gate_context(human_approved=True))

    assert result.thresholds["unresolved_contradictions==0"] is False
    assert result.verdict != "probable"
