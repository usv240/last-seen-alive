"""Score every observed pass against the sealed answer key, including the bad ones.

The stability study records what came back. This decides what it means, using the
same definition the Arm C report published:

    false_confident_identification -- "The system put forward a specific film as
    the leading candidate and the answer key says it is the wrong film."

Applying that definition across all recorded passes rather than one changes the
headline. The Arm C pass had zero. A later pass put forward "Un coin de Paris
(1900)" as the sole leading candidate on D04, where the key says "Buying a cow"
(1908). By the published definition that is one, and it is scored as one here.

Two judgement calls are unavoidable and both are made explicitly, in data, so
that a reader can disagree with a specific line rather than with a number.

**Is the label a film at all?** Several passes filled the candidate slot with
something that is not a work: a studio, a costume-period cluster, a generic
phrase. The Arm C report already treated one of these as a "malformed candidate"
rather than a misidentification, on the grounds that it identifies no film
correctly or otherwise. That precedent is followed, and every label so classified
is listed below with its reason.

**Does the label match the key?** Compared on a normalised form -- casefolded,
punctuation and a trailing parenthesised year removed -- so that "Dud Leaves Home
(1919)" matches "Dud leaves home". Nothing fuzzier than that; a near-miss on a
title is a miss.

    python scripts/score_stability.py
    python scripts/score_stability.py --write
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STABILITY = ROOT / "eval" / "reports" / "stability.json"
ARM_C = ROOT / "eval" / "reports" / "arm-c-development.json"

#: Labels observed in the candidate slot that do not name a moving-image work.
#: Each is listed with the reason it was excluded, so the judgement is auditable
#: and disputable line by line rather than hidden inside a matching rule.
NOT_A_FILM: dict[str, str] = {
    "early to mid-20th century civilian and workwear": (
        "A costume-period cluster, not a work. Already classified this way in the Arm C report."
    ),
    "bray studios inc.": (
        "A production company. Naming the studio is a real research result and may well be "
        "correct, but it identifies no film, so it is neither a hit nor a misidentification."
    ),
    "an unidentified film fragment": (
        "A restatement of the input. It names nothing and cannot be right or wrong."
    ),
    "those who pay": (
        "The incorrect label the fragment arrived carrying. Returning the supplied label is a "
        "failure to contradict it, not a new identification put forward by the system."
    ),
    "Military subjects. Soldiers on horseback (ca. 1920-ca. 1950)": (
        "A subject heading with a date range, in the form archives use to describe unidentified "
        "footage. It names no work."
    ),
    "Men's outdoor and equestrian attire from late 19th to early 20th century": (
        "A costume description, the same failure mode as the workwear cluster above."
    ),
}


def normalise(title: str) -> str:
    text = title.casefold().strip()
    text = re.sub(r"\s*\(\s*\d{4}\s*\)\s*$", "", text)   # trailing year
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


#: The labels above are written as they were observed, so they stay readable and
#: disputable. They have to be compared in the same normalised form as the
#: candidate label or a stray hyphen or full stop silently reclassifies a
#: malformed candidate as a misidentification -- which is exactly what happened
#: on the first run of this scorer, inflating the false-confident count from one
#: to three.
_NOT_A_FILM_NORMALISED = {}


def _not_a_film() -> dict[str, str]:
    if not _NOT_A_FILM_NORMALISED:
        for label, reason in NOT_A_FILM.items():
            _NOT_A_FILM_NORMALISED[normalise(label)] = reason
    return _NOT_A_FILM_NORMALISED


def classify(label: str | None, expected: str | None) -> tuple[str, str]:
    """Return (classification, why)."""
    if not label:
        return "no_candidate", "The system put no candidate forward."
    key = normalise(label)
    if key in _not_a_film():
        return "malformed_candidate", _not_a_film()[key]
    if not expected:
        return "unscored", "No expected title recorded for this case."
    want = normalise(expected)
    if want and (want == key or want in key or key in want):
        return "correct", f"Matches the answer key ({expected})."
    return "false_confident", (
        f"A specific film was put forward as the leading candidate; the answer key says "
        f"{expected}."
    )


def main() -> int:
    if not STABILITY.exists():
        print("no stability study on file; run scripts/run_stability.py --write first")
        return 1

    report = json.loads(STABILITY.read_text(encoding="utf-8"))
    expected_by_case = {}
    if ARM_C.exists():
        for record in json.loads(ARM_C.read_text(encoding="utf-8"))["results"]:
            expected_by_case[record["case_id"]] = record.get("expected_title")

    totals = {
        "correct": 0, "false_confident": 0, "malformed_candidate": 0,
        "no_candidate": 0, "unscored": 0,
    }
    reached_probable = 0

    for case in report["results"]:
        expected = expected_by_case.get(case["case_id"])
        case["expected_title"] = expected
        for observation in case["observations"]:
            classification, why = classify(observation.get("top_candidate"), expected)
            observation["classification"] = classification
            observation["classification_reason"] = why
            totals[classification] += 1
            if observation["verdict"] == "probable":
                reached_probable += 1
        counts: dict[str, int] = {}
        for observation in case["observations"]:
            counts[observation["classification"]] = counts.get(observation["classification"], 0) + 1
        case["classification_counts"] = counts

    report["scoring"] = {
        "definition": (
            "false_confident_identification: the system put forward a specific film as the "
            "leading candidate and the answer key says it is the wrong film. This is the "
            "definition published with the Arm C report, applied here to every recorded pass "
            "rather than to one."
        ),
        "totals": totals,
        "runs_scored": sum(totals.values()),
        "runs_that_reached_probable": reached_probable,
        "headline_correction": (
            "The Arm C pass recorded zero false-confident identifications and two correct "
            "identities. Across every recorded pass those figures do not hold: the system is "
            "not stable enough for a single pass to stand as its result. Both numbers are "
            "reported here over all passes."
        ),
        "what_did_hold": (
            "No run in any pass reached `probable`. Every false-confident identification "
            "counted above was returned as `candidates` with the failing thresholds attached, "
            "which is the difference between a system that is wrong and a system that asserts "
            "something wrong. It is a weaker claim than 'never wrong' and it is the true one."
        ),
        "judgement_calls": {
            "labels_treated_as_not_a_film": NOT_A_FILM,
            "note": (
                "Each label above was excluded from scoring as a misidentification because it "
                "names no work. That is a judgement, and a self-serving one if left unchecked, "
                "so both readings are published: `totals` applies the judgement, and "
                "`false_confident_upper_bound` is what the count becomes if every one of these "
                "is instead treated as a wrong identification. Quote whichever you find more "
                "defensible; neither is hidden."
            ),
            "false_confident_strict": totals["false_confident"],
            "false_confident_upper_bound": (
                totals["false_confident"] + totals["malformed_candidate"]
            ),
        },
        "matching": (
            "Casefolded, punctuation stripped, a trailing parenthesised year removed, then "
            "exact or containment match. Nothing fuzzier: a near-miss on a title is a miss."
        ),
    }

    print("Across every recorded pass:")
    for name, count in totals.items():
        print(f"  {name:22} {count}")
    print(f"  {'reached probable':22} {reached_probable}")

    if "--write" in sys.argv:
        STABILITY.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
        print(f"\nwrote {STABILITY}")
    else:
        print("\n(not written; pass --write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
