"""The scorer decides what counts as a wrong identification, so it has to be right.

This file exists because the first version of `scripts/score_stability.py` was
wrong in the direction that flatters nobody but is still wrong: the labels it
treats as "not a film" were written as observed, with their punctuation, while
the candidate labels they were compared against had punctuation stripped. Two
entries therefore never matched, and two malformed candidates were counted as
false-confident identifications. The published count went from three to one when
it was fixed.

A number that decides whether this project can claim safety must not depend on a
full stop, so both directions are pinned here: every documented not-a-film label
really is excluded, and a genuinely wrong film really is counted.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "score_stability", ROOT / "scripts" / "score_stability.py"
)
scorer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scorer)


@pytest.mark.parametrize("label", list(scorer.NOT_A_FILM))
def test_every_documented_non_film_label_is_actually_excluded(label: str) -> None:
    """The bug: a hyphen or a full stop made these fall through to false_confident."""
    classification, _ = scorer.classify(label, "Buying a cow")
    assert classification == "malformed_candidate", (
        f"{label!r} is documented as not a film but scored as {classification}"
    )


def test_the_exclusion_list_survives_punctuation_and_case() -> None:
    for variant in ("Bray Studios Inc", "BRAY STUDIOS INC.", "bray  studios   inc."):
        classification, _ = scorer.classify(variant, "Dud leaves home")
        assert classification == "malformed_candidate", variant


def test_a_wrong_film_is_counted_as_false_confident() -> None:
    """The number this whole project's safety claim rests on."""
    classification, why = scorer.classify("Un coin de Paris (1900)", "Buying a cow")
    assert classification == "false_confident"
    assert "Buying a cow" in why


def test_the_right_film_is_counted_correct_despite_case_and_year() -> None:
    classification, _ = scorer.classify("Dud Leaves Home (1919)", "Dud leaves home")
    assert classification == "correct"


def test_no_candidate_is_neither_right_nor_wrong() -> None:
    classification, _ = scorer.classify(None, "Ghosts")
    assert classification == "no_candidate"


def test_a_near_miss_on_a_title_is_a_miss() -> None:
    """Nothing fuzzier than containment: 'The Rival Brothers' is not the answer."""
    classification, _ = scorer.classify(
        "The Rival Sisters (1911)", "The rival brothers' patriotism"
    )
    assert classification == "false_confident"


def test_excluding_a_label_can_only_ever_lower_the_false_confident_count() -> None:
    """The exclusion list must not be a way to hide a wrong film.

    Every excluded label is checked against every answer-key title in the corpus:
    if one of them ever matched a real expected title, excluding it would be
    suppressing a *correct* answer rather than discounting a malformed one.
    """
    import json

    key_path = ROOT / "eval" / "answer_key" / "ground_truth.json"
    records = json.loads(key_path.read_text(encoding="utf-8-sig"))
    titles = {scorer.normalise(r["expected_title"]) for r in records if r.get("expected_title")}

    for label in scorer.NOT_A_FILM:
        assert scorer.normalise(label) not in titles, (
            f"{label!r} is excluded as 'not a film' but it is an actual answer-key title"
        )


@pytest.mark.skipif(
    not (ROOT / "eval" / "reports" / "stability.json").exists(),
    reason="no stability study on file",
)
class TestPublishedStudy:
    def test_the_published_study_is_scored(self) -> None:
        import json

        report = json.loads(
            (ROOT / "eval" / "reports" / "stability.json").read_text(encoding="utf-8")
        )
        assert "scoring" in report, "the study was published without being scored"
        totals = report["scoring"]["totals"]
        assert report["scoring"]["runs_scored"] == sum(totals.values())

    def test_the_study_publishes_its_own_bad_news(self) -> None:
        import json

        report = json.loads(
            (ROOT / "eval" / "reports" / "stability.json").read_text(encoding="utf-8")
        )
        scoring = report["scoring"]
        assert "headline_correction" in scoring, (
            "a study that contradicts the published headline must say so"
        )
        assert scoring["runs_that_reached_probable"] == 0, (
            "probable was reached without a human, which the gate is supposed to forbid"
        )
