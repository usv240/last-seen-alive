"""Capture a complete dossier for every development fragment, once, for publication.

The Arm C measurement recorded scores and threw the dossiers away. That left the
site with a defensible claim and nothing to show for it: to see what this product
actually produces you had to start a run and wait six minutes. A reader who will
not wait six minutes never sees the output at all, which is most readers.

So this runs the five development fragments through the deployed service -- the
real production path, same key, same code -- and writes each full response to
eval/reports/dossiers/. Those become the worked examples the site serves
instantly.

    python scripts/capture_dossiers.py
    python scripts/capture_dossiers.py https://your-own-deployment.example

It refuses the held-out split. A published artifact of a held-out case would
burn the one unrepeatable measurement this project has.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

BASE = (sys.argv[1] if len(sys.argv) > 1 else
        "https://last-seen-alive-109051079423.us-central1.run.app").rstrip("/")
OUT = Path(__file__).resolve().parents[1] / "eval" / "reports" / "dossiers"

# A run measured 225-430s. The ceiling here is the Cloud Run request timeout,
# because a client that gives up earlier than the server does turns a completed
# investigation into a lost one.
REQUEST_TIMEOUT = 900


def call(path: str, *, method: str = "GET", key: str | None = None,
         body: dict | None = None) -> tuple[int, dict]:
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


def main() -> int:
    status, minted = call("/v1/keys", method="POST", body={"tier": "judge"})
    if status != 200:
        print(f"could not mint a key: HTTP {status}")
        return 1
    key = minted["data"]["key"]

    status, presets = call("/v1/presets")
    runnable = [row for row in presets["data"]["presets"] if row["runnable"]]
    if not runnable:
        print("no runnable presets")
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    index: list[dict] = []

    print(f"Capturing {len(runnable)} dossiers from {BASE}")
    print("Each run is a real investigation against live sources. Expect ~30 minutes total.\n")

    for row in runnable:
        case_id = row["case_id"]
        if row.get("split") != "dev":
            print(f"  {case_id}: refusing, not a development case")
            continue

        print(f"  {case_id} ... ", end="", flush=True)
        started = time.time()
        status, payload = call("/v1/identify", method="POST", key=key,
                               body={"sample_id": case_id})
        elapsed = time.time() - started

        if status != 200:
            print(f"HTTP {status} after {elapsed:.0f}s -- {payload}")
            continue

        meta = payload.get("meta", {})
        # The capture is evidence, so it records when and against what it ran.
        payload["captured"] = {
            "at": datetime.now(UTC).isoformat(),
            "service": BASE,
            "elapsed_seconds": round(elapsed, 1),
            "note": (
                "A real run of the deployed service on a public Library of Congress "
                "fragment. Not edited, not curated, not re-run to get a better result."
            ),
        }
        (OUT / f"{case_id}.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        verdict = meta.get("verdict", "?")
        print(f"{verdict} in {elapsed:.0f}s")
        index.append({
            "case_id": case_id,
            "title": row.get("title") or row.get("label"),
            "verdict": verdict,
            "expected_outcome": row.get("expected_outcome"),
            "elapsed_seconds": round(elapsed, 1),
            "thresholds_passed": len(meta.get("gate", {}).get("passed", [])),
            "parallel_surfaces_used": meta.get("parallel_surfaces_used", []),
        })

    (OUT / "index.json").write_text(
        json.dumps({
            "captured_at": datetime.now(UTC).isoformat(),
            "service": BASE,
            "split": "dev",
            "dossiers": index,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nWrote {len(index)} dossiers to {OUT}")
    return 0 if index else 1


if __name__ == "__main__":
    raise SystemExit(main())
