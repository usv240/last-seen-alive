"""Did the competing-hypotheses fix actually change anything?

Two defects were found by running the development split repeatedly: candidates
that were not films, and hypotheses that nothing ever opposed. Two fixes went in
-- `app/works.py` type-checks the candidate slot, and the identity gate gained
`competing_hypotheses>=2` and `leading_hypothesis_least_contradicted` from
Heuer's Analysis of Competing Hypotheses.

A fix that is not measured is a hope. This merges the runs recorded before the
change with the runs recorded after it and reports both, so the claim in the
commit message can be checked rather than believed.

The eras are told apart by the gate itself: a run scored by the old gate carries
seven thresholds, a run scored by the new one carries nine. That is a property of
the recorded data, not a label applied by hand.

    python scripts/compare_fix.py
    python scripts/compare_fix.py --write

**n is small.** Around ten runs an era, five fragments. This is a disclosure of
direction, not a rate, and the report says so in its own text.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BEFORE = ROOT / "eval" / "reports" / "stability-before-fix.json"
AFTER = ROOT / "eval" / "reports" / "stability.json"
OUT = ROOT / "eval" / "reports" / "fix-comparison.json"

# scripts/ is a directory of entry points, not a package, so the scorer is loaded
# by path. Sharing it matters more than the awkwardness: both eras have to be
# judged by exactly the same rules or the comparison means nothing.
_SPEC = importlib.util.spec_from_file_location(
    "score_stability", Path(__file__).with_name("score_stability.py")
)
_SCORER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_SCORER)
classify = _SCORER.classify


def _observations(path: Path) -> list[dict]:
    if not path.exists():
        return []
    report = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for case in report["results"]:
        for observation in case["observations"]:
            rows.append({**observation, "case_id": case["case_id"],
                         "expected_title": case.get("expected_title")})
    return rows


def _key(observation: dict) -> tuple:
    """Identify a run so the same one is not counted in both eras."""
    return (
        observation["case_id"],
        observation.get("source"),
        observation.get("latency_seconds"),
        observation.get("top_candidate"),
    )


def summarise(rows: list[dict], label: str) -> dict:
    totals = Counter()
    for row in rows:
        classification, _ = classify(row.get("top_candidate"), row.get("expected_title"))
        row["classification"] = classification
        totals[classification] += 1

    by_case: dict[str, list[str]] = {}
    for row in rows:
        by_case.setdefault(row["case_id"], []).append(row["verdict"])
    stable = [case for case, verdicts in by_case.items() if len(set(verdicts)) == 1]

    return {
        "era": label,
        "runs": len(rows),
        "cases": len(by_case),
        "cases_with_a_stable_verdict": len(stable),
        "correct": totals["correct"],
        "false_confident": totals["false_confident"],
        "candidates_naming_no_film": totals["malformed_candidate"],
        "no_candidate": totals["no_candidate"],
        "reached_probable": sum(1 for row in rows if row["verdict"] == "probable"),
    }


def main() -> int:
    before = _observations(BEFORE)
    after_all = _observations(AFTER)

    seen = {_key(row) for row in before}
    after = [row for row in after_all if _key(row) not in seen]

    if not before or not after:
        print("need both a before and an after study on file")
        return 1

    before_summary = summarise(before, "before the fix")
    after_summary = summarise(after, "after the fix")

    report = {
        "study": "competing_hypotheses_fix",
        "generated_at": datetime.now(UTC).isoformat(),
        "what_changed": [
            "app/works.py type-checks the candidate slot so a studio, a piece of leader, "
            "a costume cluster or a restatement of the input cannot be scored as an identity.",
            "The identity gate gained competing_hypotheses>=2 and "
            "leading_hypothesis_least_contradicted, from Heuer's Analysis of Competing "
            "Hypotheses. Seven thresholds became nine.",
            "The Skeptic is asked to find a rival identity rather than only attack the "
            "incumbent, and the compiler is told a lone candidate will not pass.",
        ],
        "before": before_summary,
        "after": after_summary,
        "honest_reading": (
            "Around ten runs an era over five fragments. This shows direction, not a rate, and "
            "no percentage should be quoted from it. The candidates_naming_no_film figure is "
            "the least interesting of the numbers because the filter removes those by "
            "construction; the ones worth reading are false_confident and "
            "cases_with_a_stable_verdict, which the filter does not directly control."
        ),
        "observations": {"before": before, "after": after},
    }

    def line(name: str, key: str) -> None:
        print(f"  {name:34} {before_summary[key]:>6}  ->{after_summary[key]:>5}")

    print(f"\nBefore: {before_summary['runs']} runs   After: {after_summary['runs']} runs\n")
    line("correct identities", "correct")
    line("false-confident identifications", "false_confident")
    line("candidates naming no film", "candidates_naming_no_film")
    line("no candidate offered", "no_candidate")
    line("cases with a stable verdict", "cases_with_a_stable_verdict")
    line("runs reaching probable", "reached_probable")

    if "--write" in sys.argv:
        OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nwrote {OUT}")
    else:
        print("\n(not written; pass --write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
