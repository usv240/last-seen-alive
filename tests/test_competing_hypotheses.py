"""The two defects the stability study found, and the fixes for them.

Nineteen recorded runs of the development split produced two failures that a
single pass had hidden:

**Seven candidates were not films.** A production company, a piece of leader, a
restatement of the input, two costume clusters. The schema asked for a candidate
identity and accepted any noun phrase.

**Hypotheses were never opposed.** D04 produced exactly one candidate on every
run and then agreed with it fourteen times, reaching five of seven thresholds on
the wrong film in three runs out of four. Nothing could discriminate, because
there was nothing to discriminate against.

The fixes are `app/works.py` (type-check the candidate slot) and two thresholds
in the identity gate taken from Heuer's Analysis of Competing Hypotheses. Both
are tested here against the labels actually observed, not against invented ones.
"""

from __future__ import annotations

import pytest

from agentic_core.evidence import Claim, Source, stable_claim_id
from agentic_core.gate import Candidate
from app import works
from app.gates import IdentityGate

from test_identity_gate import complete_context, sourced_claim

# ------------------------------------------------------------- the type check

#: Every label this pipeline actually put in a candidate slot across 19 runs and
#: that is not a film, with the observed spelling.
OBSERVED_NON_WORKS = [
    "Bray Studios Inc.",
    "An unidentified film fragment",
    "Black film leader",
    "Early to Mid-20th Century Civilian and Workwear",
    "Military subjects. Soldiers on horseback (ca. 1920-ca. 1950)",
    "Men's outdoor and equestrian attire from late 19th to early 20th century",
    "Fragment D03 visuals",
    "Library of Congress National Screening Room",
]

#: Real titles from the answer key and the runs, which must survive. A filter
#: that rejects these is worse than no filter.
MUST_SURVIVE = [
    "Dud Leaves Home",
    "Through the Breakers",
    "Un coin de Paris",
    "The Artist's Dream",
    "Bobby Bumps at the Circus",
    "The Tale of a Wag",
    "Ghosts",
    "Buying a cow",
    "The rival brothers' patriotism",
    "Those who pay",
    "A Corner in Wheat",
    "The Great Train Robbery",
    "Le Voyage dans la Lune",
    # Near-misses for the rules, deliberately: these must not trip them.
    "Museum Hours",
    "The Company She Keeps",
]


@pytest.mark.parametrize("label", OBSERVED_NON_WORKS)
def test_observed_non_films_are_rejected_with_a_reason(label: str) -> None:
    accepted, reason = works.classify(label)
    assert not accepted, f"{label!r} was accepted as a film"
    assert ":" in reason, "a rejection must name the rule and explain it"


@pytest.mark.parametrize("title", MUST_SURVIVE)
def test_real_titles_survive_the_filter(title: str) -> None:
    accepted, reason = works.classify(title)
    assert accepted, f"{title!r} is a real title but was rejected: {reason}"


def test_no_pattern_carries_a_corrupted_escape() -> None:
    """A shell heredoc once turned this module's \\b into a literal backspace.

    The regex still compiled and still matched *nothing*, so the filter silently
    passed everything it was supposed to catch. A test is cheaper than finding
    that again by hand.
    """
    for name in dir(works):
        value = getattr(works, name)
        pattern = getattr(value, "pattern", None)
        if isinstance(pattern, str):
            assert "\x08" not in pattern, f"{name} contains a literal backspace byte"


def test_an_empty_title_is_not_a_candidate() -> None:
    accepted, reason = works.classify("")
    assert not accepted
    assert "empty_title" in reason


# ------------------------------------------------- competing hypotheses (ACH)

def _rival(candidate_id: str = "rival-1", *, score: float = 0.4) -> Candidate:
    return Candidate(candidate_id=candidate_id, label="A Rival Film", score=score,
                     decisive_claim_ids=())


def test_a_lone_hypothesis_cannot_reach_probable() -> None:
    """The D04 failure, reproduced and then blocked.

    Everything else about this fixture is perfect: three independent domains, two
    clue families, compatible dates and entities, sourced decisive claims, and a
    human who has approved it. One candidate is the only thing wrong, and it is
    enough, because an unopposed hypothesis has not been tested.
    """
    claims = [sourced_claim(f"archive{i}.example.org") for i in range(3)]
    context = dict(complete_context(claims))
    context["candidates"] = [context["candidates"][0]]  # drop the rival

    result = IdentityGate().evaluate(claims, context)
    assert result.verdict != "probable", "a single unopposed candidate reached probable"
    assert result.thresholds["competing_hypotheses>=2"] is False
    assert "competing_hypotheses>=2" in result.failed


def test_the_same_case_passes_once_a_rival_exists() -> None:
    """Proves the previous test is about opposition, not about some other defect."""
    claims = [sourced_claim(f"archive{i}.example.org") for i in range(3)]
    result = IdentityGate().evaluate(claims, complete_context(claims))
    assert result.verdict == "probable"
    assert result.thresholds["competing_hypotheses>=2"] is True


def test_the_leading_hypothesis_must_not_be_the_most_contradicted() -> None:
    """Heuer's inversion: prefer the least inconsistent hypothesis, not the best supported."""
    claims = [sourced_claim(f"archive{i}.example.org") for i in range(3)]
    contradiction = Claim(
        claim_id=stable_claim_id("film-42", "contradicts", "rebuttal.example.org"),
        claim_text="The release date is incompatible with the stock.",
        subject="film-42",
        agent_id="skeptic",
        stance="contradicts",
        sources=(
            Source(
                url="https://rebuttal.example.org/record",
                domain="rebuttal.example.org",
                excerpt="The stock was manufactured after the claimed release.",
                retrieved_at=claims[0].sources[0].retrieved_at,
                verified=True,
            ),
        ),
        confidence_basis="A dated source contradicts the leading candidate.",
    )

    context = dict(complete_context(claims))
    result = IdentityGate().evaluate([*claims, contradiction], context)

    assert result.thresholds["leading_hypothesis_least_contradicted"] is False, (
        "the leading candidate carries a contradiction its rival does not, and the gate "
        "did not notice"
    )
    assert result.verdict != "probable"


def test_the_gate_publishes_nine_thresholds() -> None:
    """The count is quoted across the product; it must not drift silently."""
    claims = [sourced_claim(f"archive{i}.example.org") for i in range(3)]
    result = IdentityGate().evaluate(claims, complete_context(claims))
    assert len(result.thresholds) == 9
    for required in ("competing_hypotheses>=2", "leading_hypothesis_least_contradicted"):
        assert required in result.thresholds
