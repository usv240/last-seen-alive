"""Measure the control arm on the development split.

    python scripts/run_ablation.py                       # one pass at temperature 0
    python scripts/run_ablation.py --repeats 3 --temp 0.7  # sample a realistic run
    python scripts/run_ablation.py --write               # write eval/reports/ablation-control.json

A single greedy sample is one data point, not a measurement. Repeats at a
non-zero temperature show whether the behaviour is stable or whether the
greedy answer was a lucky draw.

Needs Vertex AI only. It deliberately does NOT need the Parallel credential,
because the whole point is to measure what a capable multimodal model does
*without* any of the research and gating this product adds.

Development split only. The held-out fragments stay sealed for every arm; a
baseline is not a licence to open them.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentic_core.eval import EvaluationCorpus  # noqa: E402
from app.ablation import run_control, summarise, summarise_gated  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parents[1] / "eval"
OUT = EVAL_DIR / "reports" / "ablation-control.json"


def _flag(name: str, default: str) -> str:
    if name in sys.argv:
        index = sys.argv.index(name)
        if index + 1 < len(sys.argv):
            return sys.argv[index + 1]
    return default


def main() -> int:
    corpus = EvaluationCorpus(EVAL_DIR)
    problems = corpus.verify()
    if problems:
        print("corpus is not evaluable:")
        for p in problems:
            print("  -", p)
        return 1

    files = corpus.files()
    dev_ids = corpus.ids_for("dev")
    expected = {cid: corpus.manifest[cid]["expected_outcome"] for cid in dev_ids}

    print(f"Control arm over {len(dev_ids)} development fragments")
    print("Gemini alone: no web access, no citation checking, no gate.\n")

    repeats = int(_flag("--repeats", "1"))
    temperature = float(_flag("--temp", "0.0"))
    if repeats > 1 or temperature:
        print(f"  {repeats} pass(es) per case at temperature {temperature}\n")

    results = []
    for case_id in dev_ids:
        row = corpus.manifest[case_id]
        for attempt in range(repeats):
            suffix = f" [{attempt + 1}/{repeats}]" if repeats > 1 else ""
            print(
                f"  {case_id} ({row['tier']}, must {row['expected_outcome']}){suffix} ... ",
                end="", flush=True,
            )
            result = run_control(
                case_id=case_id,
                fragment_path=files[case_id],
                media_type=row["media_type"],
                provided_label=row.get("provided_label"),
                temperature=temperature,
            )
            results.append(result)
            if result.error:
                print(f"ERROR {result.error[:60]}")
            elif result.names_a_film:
                sourced = "cited" if result.citable_sources else "NO SOURCE"
                print(
                    f'names "{result.title}" ({result.year or "?"}) '
                    f'· {result.confidence} · {sourced}'
                )
            else:
                print(f"names no film · confidence {result.confidence}")

    report = summarise(results, expected)
    report["generated_at"] = datetime.now(UTC).isoformat()
    report["split"] = "dev"
    report["model"] = "gemini-2.5-flash"
    report["repeats_per_case"] = repeats
    report["temperature"] = temperature
    report["expected_outcomes"] = expected

    # Arm B costs nothing extra: it is the control's own answers put through the
    # production evidence builder and gate, with an empty citation registry.
    report["arm_b_control_plus_gate"] = summarise_gated(results)

    print("\n" + "=" * 72)
    print(f"  runs                                         {report['runs']} over {report['cases']} cases")
    print(f"  runs where no identification is possible     {report['runs_where_no_identification_is_possible']}")
    print(f"  false-confident identifications              {report['false_confident_identifications']}"
          f"  {report['false_confident_case_ids'] or ''}")
    print(f"  identifications made                         {report['identifications_made']}")
    print(f"  ...with NO citable source                    {report['identifications_with_no_citable_source']}"
          f"   (rate {report['unsourceable_identification_rate']})")
    print(f"  ignored the supplied catalogue label         {report['runs_that_ignored_the_supplied_label']}"
          f" of {report['runs_with_a_supplied_label']}")
    if report["unstable_cases_across_repeats"]:
        print(f"  unstable across repeats                      {report['unstable_cases_across_repeats']}")
    print(f"  median latency                               {report['median_latency_ms']} ms")
    print("-" * 72)
    b = report["arm_b_control_plus_gate"]
    print("  ARM B — the same answers through the real gate")
    print(f"    control identifications                    {b['control_identifications']}")
    print(f"    surviving the gate                         {b['identifications_surviving_the_gate']}")
    print(f"    verdicts produced                          {', '.join(b['verdicts'])}")
    print("=" * 72)

    if "--write" in sys.argv:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"\nwritten to {OUT.relative_to(Path.cwd()) if OUT.is_relative_to(Path.cwd()) else OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
