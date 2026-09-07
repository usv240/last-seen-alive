"""The control arm has to stay a fair control, and its scoring has to stay honest.

The value of a baseline is entirely in its fairness. If the control quietly
gains a tool, or its scoring is bent toward the conclusion the project would
prefer, the comparison stops meaning anything.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.ablation import CONTROL_SCHEMA, ControlResult, _prompt, summarise

REPORT = Path(__file__).resolve().parents[1] / "eval" / "reports" / "ablation-control.json"


def _result(case_id, *, names=False, title="", sources=(), confidence="none", label=None):
    return ControlResult(
        case_id=case_id,
        names_a_film=names,
        title=title,
        year="",
        confidence=confidence,
        reasoning="",
        citable_sources=list(sources),
        engaged_supplied_label=label,
    )


def test_the_control_is_asked_the_same_question_a_person_would() -> None:
    """It must not be a straw man: no hedging language planted in the prompt."""
    unlabelled = _prompt(None)
    assert "Identify this archival film fragment" in unlabelled
    assert "no label of any kind" in unlabelled
    for leading in ("do not guess", "abstain", "refuse", "you must not"):
        assert leading not in unlabelled.lower(), f"prompt steers the control: {leading!r}"

    labelled = _prompt("Those who pay")
    assert "Those who pay" in labelled
    # The label is offered as uncertain, exactly as the full system receives it.
    assert "may or may not be correct" in labelled


def test_the_control_schema_lets_it_decline() -> None:
    """A control that cannot say "I don't know" would manufacture the result."""
    props = CONTROL_SCHEMA["properties"]
    assert props["names_a_film"]["type"] == "boolean"
    assert "none" in props["confidence"]["enum"]


def test_false_confident_counts_only_where_no_identification_is_possible() -> None:
    expected = {"D01": "abstain", "D02": "identify", "D03": "candidates"}
    results = [
        _result("D01", names=True, title="Something", confidence="high"),
        _result("D02", names=True, title="Legit", confidence="high"),  # allowed to name
        _result("D03", names=False),
    ]
    report = summarise(results, expected)
    assert report["false_confident_identifications"] == 1
    assert report["false_confident_case_ids"] == ["D01"]


def test_unsourceable_rate_is_over_identifications_not_over_runs() -> None:
    """Declining to name a film is not an unsourced identification."""
    expected = {"D01": "abstain", "D02": "identify", "D04": "identify"}
    results = [
        _result("D01", names=False),
        _result("D02", names=True, title="A", sources=["https://x.example.org"]),
        _result("D04", names=True, title="B"),
    ]
    report = summarise(results, expected)
    assert report["identifications_made"] == 2
    assert report["identifications_with_no_citable_source"] == 1
    assert report["unsourceable_identification_rate"] == 0.5


def test_instability_is_detected_across_repeats() -> None:
    expected = {"D02": "identify"}
    stable = [_result("D02", names=True, title="Same") for _ in range(3)]
    assert summarise(stable, expected)["unstable_cases_across_repeats"] == []

    varied = [
        _result("D02", names=True, title="One"),
        _result("D02", names=True, title="Two"),
        _result("D02", names=True, title="One"),
    ]
    assert summarise(varied, expected)["unstable_cases_across_repeats"] == ["D02"]


def test_errored_runs_are_reported_and_not_scored() -> None:
    expected = {"D01": "abstain"}
    bad = _result("D01")
    bad.error = "ResourceExhausted: quota"
    report = summarise([bad], expected)
    assert report["runs_errored"] == 1
    assert report["false_confident_identifications"] == 0


def test_the_published_report_matches_what_the_scorer_produces() -> None:
    """The committed result must be reproducible from its own raw runs.

    Guards against the report being hand-edited after the fact, which is the
    one thing that would make publishing a baseline worse than not having one.
    """
    if not REPORT.exists():
        return
    published = json.loads(REPORT.read_text(encoding="utf-8"))
    results = [
        ControlResult(
            case_id=r["case_id"],
            names_a_film=r["names_a_film"],
            title=r["title"],
            year=r["year"],
            confidence=r["confidence"],
            reasoning=r["reasoning"],
            visible_evidence=r.get("visible_evidence", []),
            citable_sources=r.get("citable_sources", []),
            latency_ms=r.get("latency_ms", 0),
            engaged_supplied_label=r.get("engaged_supplied_label"),
            error=r.get("error"),
        )
        for r in published["results"]
    ]
    recomputed = summarise(results, published["expected_outcomes"])
    for field in (
        "runs",
        "cases",
        "false_confident_identifications",
        "identifications_made",
        "identifications_with_no_citable_source",
        "unsourceable_identification_rate",
        "unstable_cases_across_repeats",
    ):
        assert recomputed[field] == published[field], f"{field} does not match its own raw runs"


def test_the_published_report_did_not_touch_the_holdout() -> None:
    """A baseline is not a licence to open the sealed split."""
    if not REPORT.exists():
        return
    published = json.loads(REPORT.read_text(encoding="utf-8"))
    assert published["split"] == "dev"
    assert all(not r["case_id"].startswith("H") for r in published["results"])
