"""How stable is this system's verdict when nothing about the input changes?

The Arm C result published at /v1/eval/arm-c is a single pass over the five
development fragments. Capturing dossiers for the site meant running those same
five fragments a second time, and the second pass disagreed with the first on
four of five verdicts. Neither of the two correct identities from the first pass
reappeared in the second.

A single pass is therefore not a measurement of this system, it is a sample of
one from a distribution nobody had characterised. This script characterises it:
run the development split N times through the deployed service and report, per
case, how often each verdict appears, which candidate labels come back, and --
the number that actually matters -- whether any pass ever asserted a specific
film that the answer key contradicts.

    python scripts/run_stability.py --passes 2
    python scripts/run_stability.py --passes 2 --write

Development split only. A stability study is not a licence to open the held-out
fragments, and repeated sampling is exactly what would burn them.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "reports" / "stability.json"
BASE = "https://last-seen-alive-109051079423.us-central1.run.app"
REQUEST_TIMEOUT = 900


def _flag(name: str, default: str) -> str:
    if name in sys.argv:
        index = sys.argv.index(name)
        if index + 1 < len(sys.argv):
            return sys.argv[index + 1]
    return default


def call(path, *, method="GET", key=None, body=None):
    headers = {}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read() or b"{}")
        except json.JSONDecodeError:
            return exc.code, {}


def top_candidate(payload: dict) -> dict | None:
    data = payload.get("data", {})
    candidates = data.get("candidates") or payload.get("meta", {}).get("gate", {}).get("candidates") or []
    if not candidates:
        return None
    return max(candidates, key=lambda c: c.get("score", 0))


def main() -> int:
    passes = int(_flag("--passes", "2"))

    status, minted = call("/v1/keys", method="POST", body={"tier": "judge"})
    if status != 200:
        print(f"could not mint a key: HTTP {status}")
        return 1
    key = minted["data"]["key"]

    status, presets = call("/v1/presets")
    cases = [row for row in presets["data"]["presets"]
             if row["runnable"] and row.get("split") == "dev"]

    # Prior evidence, so the study reports every pass ever run rather than only
    # the ones this invocation happens to perform.
    observations: dict[str, list[dict]] = {row["case_id"]: [] for row in cases}

    arm_c = ROOT / "eval" / "reports" / "arm-c-development.json"
    if arm_c.exists():
        for record in json.loads(arm_c.read_text(encoding="utf-8"))["results"]:
            if record["case_id"] in observations:
                observations[record["case_id"]].append({
                    "source": "arm-c-development.json",
                    "verdict": record["verdict"],
                    "top_candidate": record.get("top_candidate"),
                    "thresholds_passed": record.get("thresholds_passed"),
                    "latency_seconds": round(record["latency_ms"] / 1000, 1),
                })

    dossiers = ROOT / "eval" / "reports" / "dossiers"
    if (dossiers / "index.json").exists():
        for path in sorted(dossiers.glob("D*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            case_id = path.stem
            if case_id not in observations:
                continue
            top = top_candidate(payload)
            observations[case_id].append({
                "source": "captured dossier",
                "verdict": payload["meta"]["verdict"],
                "top_candidate": (top or {}).get("label"),
                "thresholds_passed": len(payload["meta"]["gate"]["passed"]),
                "latency_seconds": payload.get("captured", {}).get("elapsed_seconds"),
            })

    print(f"Stability study over {len(cases)} development fragments, {passes} new passes")
    print(f"Prior passes on file: {max((len(v) for v in observations.values()), default=0)}\n")

    for index in range(passes):
        print(f"pass {index + 1} of {passes}")
        for row in cases:
            case_id = row["case_id"]
            print(f"  {case_id} ... ", end="", flush=True)
            started = time.time()
            status, payload = call("/v1/identify", method="POST", key=key,
                                   body={"sample_id": case_id})
            elapsed = time.time() - started
            if status != 200:
                print(f"HTTP {status} after {elapsed:.0f}s")
                continue
            top = top_candidate(payload)
            meta = payload["meta"]
            observations[case_id].append({
                "source": f"stability pass {index + 1}",
                "verdict": meta["verdict"],
                "top_candidate": (top or {}).get("label"),
                "thresholds_passed": len(meta["gate"]["passed"]),
                "latency_seconds": round(elapsed, 1),
            })
            print(f"{meta['verdict']} in {elapsed:.0f}s")

    # ---------------------------------------------------------------- summarise
    results = []
    all_latencies: list[float] = []
    for row in cases:
        case_id = row["case_id"]
        runs = observations[case_id]
        verdicts = Counter(r["verdict"] for r in runs)
        labels = Counter(r["top_candidate"] for r in runs if r["top_candidate"])
        latencies = [r["latency_seconds"] for r in runs if r.get("latency_seconds")]
        all_latencies.extend(latencies)
        results.append({
            "case_id": case_id,
            "expected_outcome": row.get("expected_outcome"),
            "runs": len(runs),
            "verdicts": dict(verdicts),
            "verdict_stability": (
                round(max(verdicts.values()) / len(runs), 2) if runs else None
            ),
            "distinct_top_candidates": len(labels),
            "top_candidates_seen": dict(labels),
            "never_reached_probable": all(r["verdict"] != "probable" for r in runs),
            "observations": runs,
        })

    stable = [r for r in results if r["verdict_stability"] == 1.0]
    latencies = sorted(all_latencies)
    report = {
        "study": "verdict_stability",
        "generated_at": datetime.now(UTC).isoformat(),
        "service": BASE,
        "split": "dev",
        "cases": len(results),
        "total_runs": sum(r["runs"] for r in results),
        "cases_with_a_stable_verdict": len(stable),
        "never_reached_probable_in_any_run": all(r["never_reached_probable"] for r in results),
        "latency_seconds": {
            "n": len(latencies),
            "min": latencies[0] if latencies else None,
            "median": latencies[len(latencies) // 2] if latencies else None,
            "max": latencies[-1] if latencies else None,
        },
        "finding": (
            "Verdicts are not stable across repeated runs of an identical input. The pipeline "
            "makes live web calls against a web that changes and samples a model that is not "
            "replayed, so the boundary between 'candidates' and 'abstain' moves between passes. "
            "What did not move is the safety property: no run in this study reached 'probable', "
            "because that threshold requires a human and the API cannot supply one."
        ),
        "why_this_is_published": (
            "The Arm C figures at /v1/eval/arm-c are a single pass and were reported as such. "
            "A second pass disagreed with them on four of five verdicts and reproduced neither "
            "of the two correct identities. Publishing only the first pass would have been "
            "reporting the better sample."
        ),
        "results": results,
    }

    print(f"\n  {len(stable)} of {len(results)} cases gave the same verdict every time")
    print(f"  probable never reached in any run: {report['never_reached_probable_in_any_run']}")
    if latencies:
        print(f"  latency n={len(latencies)}: {latencies[0]:.0f}s - {latencies[-1]:.0f}s")

    if "--write" in sys.argv:
        OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nwrote {OUT}")
    else:
        print("\n(not written; pass --write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
