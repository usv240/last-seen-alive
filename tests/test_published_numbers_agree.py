"""Every surface must quote the same evaluation numbers as the report on disk.

A reviewer caught this before a judge could: the demo narration said 28 runs
while the landing page, the README and the dossier page still said 19, because
the study had been re-run and the prose had not. A judge who notices the
narration and the screen disagreeing has been handed a reason to distrust every
other number in the submission, and that is a far worse outcome than quoting the
older figure consistently.

Prose drifts; a test does not. These read `eval/reports/stability.json` and
assert that no shipped surface contradicts it.

The rule is about *contradiction*, not about mentioning a number. Historical
statements are fine and necessary -- "over the first 19 recorded runs" describes
a real earlier era and must stay sayable. What must never appear is a claim about
the current total that disagrees with the current total.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "eval" / "reports" / "stability.json"

#: Everything a judge can read or hear.
SURFACES = [
    "README.md",
    "STATUS.md",
    "app/web/index.html",
    "app/web/dossiers.html",
    "docs/ABLATION.md",
    "docs/LIMITATIONS.md",
    "docs/DEMO-SCRIPT.md",
    "docs/DEMO-VIDEO.md",
    "submission-evidence.json",
]

WORDS = {
    19: "nineteen", 20: "twenty", 28: "twenty-eight", 29: "twenty-nine",
    5: "five", 9: "nine", 12: "twelve", 16: "sixteen",
}


@pytest.fixture(scope="module")
def study() -> dict:
    report = json.loads(STUDY.read_text(encoding="utf-8"))
    scoring = report["scoring"]
    return {
        "runs": report["total_runs"],
        "false_confident": scoring["totals"]["false_confident"],
        "upper_bound": scoring["judgement_calls"]["false_confident_upper_bound"],
        "probable": scoring["runs_that_reached_probable"],
    }


@pytest.mark.parametrize("surface", SURFACES)
def test_no_surface_claims_a_stale_total(surface: str, study: dict) -> None:
    """"Across N runs" must name the real N, in digits or in words."""
    text = (ROOT / surface).read_text(encoding="utf-8")
    runs = study["runs"]

    patterns = [
        r"[Aa]cross (?:all )?(\d+) runs",
        r"[Oo]ver (\d+) recorded runs",
        r"\| Across (\d+) runs \|",
        r"in (\d+) runs it never",
    ]
    for pattern in patterns:
        for found in re.findall(pattern, text):
            assert int(found) == runs, (
                f"{surface} says '{found} runs' but the study records {runs}. "
                "Update the surface or re-run the study; do not let them disagree."
            )

    spoken = WORDS.get(runs)
    stale_words = {word for value, word in WORDS.items()
                   if value in (19, 20, 28, 29) and word != spoken}
    for word in stale_words:
        for phrase in (f"same five fragments {word} times", f"in {word} runs",
                       f"across {word} runs"):
            assert phrase not in text.lower(), (
                f"{surface} spells out '{phrase}' but the study records {runs} runs"
            )


@pytest.mark.parametrize("surface", SURFACES)
def test_no_surface_understates_the_false_confident_count(surface: str, study: dict) -> None:
    """The number that matters most is the one it would be most tempting to leave stale."""
    text = (ROOT / surface).read_text(encoding="utf-8")
    actual = study["false_confident"]

    for found in re.findall(r"there (?:are|were) \*{0,2}(\w+)\*{0,2} false-confident", text):
        value = WORDS_REVERSED.get(found.lower(), found)
        try:
            value = int(value)
        except (TypeError, ValueError):
            continue
        assert value == actual, (
            f"{surface} says {found!r} false-confident identifications; the study records {actual}"
        )


WORDS_REVERSED = {word: value for value, word in WORDS.items()}


def test_the_probable_guarantee_is_never_softened(study: dict) -> None:
    """The one property every measurement has agreed on. It must stay absolute."""
    assert study["probable"] == 0, (
        "a run reached `probable` without a human; the central safety claim is now false "
        "and every surface asserting it must be corrected before anything ships"
    )


def test_the_demo_script_matches_the_study(study: dict) -> None:
    """The narration is the one surface a judge cannot re-read to check."""
    text = (ROOT / "docs" / "DEMO-SCRIPT.md").read_text(encoding="utf-8")
    runs_word = WORDS[study["runs"]]
    fc_word = WORDS[study["false_confident"]]

    assert f"fragments {runs_word} times" in text.lower(), (
        f"the script must say '{runs_word} times' to match the study's {study['runs']} runs"
    )
    assert f"wrong film {fc_word} times" in text.lower(), (
        f"the script must say the wrong film was named '{fc_word}' times "
        f"to match the study's {study['false_confident']}"
    )
    assert f"in {runs_word} runs it never once claimed a probable identity" in text.lower()
