"""Every latency the product states must match the latency it measured.

This test exists because of a real defect. The run console's stage timings were
written from an estimate totalling 100 seconds, before a Parallel credential
existed. When the credential was attached the measured median came in at 383
seconds. Nothing failed: the console simply walked through all six stages in
under two minutes and then sat on the last one for four more, with a live clock
ticking. The file's own opening comment says it exists so that a long wait does
not read as a hang, and the stale numbers made it produce precisely that.

Three surfaces quoted the same stale range in prose. A number repeated in four
places drifts in four places, so the check is mechanical rather than editorial:
the console's own stage total, and any duration written into a user-facing page,
are compared against the measured report on disk.

If a new measurement moves the median, this test fails until the console and the
pages are moved with it. That is the point.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "eval" / "reports" / "arm-c-development.json"
CONSOLE = ROOT / "app" / "web" / "console.js"

#: The stage cadence is a shape, not an instrument, so it does not have to equal
#: the median exactly. It does have to land in the same part of the minute, or
#: the console runs out of stages while the request is still in flight.
TOLERANCE = 0.25


@pytest.fixture(scope="module")
def measured() -> dict[str, float]:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    latencies = sorted(r["latency_ms"] / 1000 for r in report["results"])
    return {
        "median": report["median_latency_ms"] / 1000,
        "low": latencies[0],
        "high": latencies[-1],
    }


def _stage_seconds() -> list[int]:
    source = CONSOLE.read_text(encoding="utf-8")
    block = re.search(r"const STAGES = \[(.*?)\n  \];", source, re.S)
    assert block, "STAGES array not found; this test needs updating with the console"
    return [int(match) for match in re.findall(r",\s*(\d+)\],", block.group(1))]


def test_the_console_walks_for_about_as_long_as_a_run_actually_takes(measured) -> None:
    total = sum(_stage_seconds())
    median = measured["median"]
    assert abs(total - median) <= median * TOLERANCE, (
        f"the console narrates {total}s of work but a run measures {median:.0f}s. "
        "A viewer watching the last stage for the difference reads it as a hang."
    )


def test_every_stage_has_a_positive_duration() -> None:
    stages = _stage_seconds()
    assert len(stages) == 6, f"expected six named stages, found {len(stages)}"
    assert all(seconds > 0 for seconds in stages), "a zero-length stage is never seen"


def test_the_console_quotes_the_measured_spread(measured) -> None:
    """The up-front estimate must come from the report, not from memory."""
    source = CONSOLE.read_text(encoding="utf-8")
    low = int(re.search(r"const TYPICAL_LOW = (\d+);", source).group(1))
    high = int(re.search(r"const TYPICAL_HIGH = (\d+);", source).group(1))

    assert low == pytest.approx(measured["low"], abs=5), (
        f"console promises a floor of {low}s; the fastest measured run was {measured['low']:.0f}s"
    )
    assert high == pytest.approx(measured["high"], abs=5), (
        f"console promises a ceiling of {high}s; the slowest measured run was {measured['high']:.0f}s"
    )


@pytest.mark.parametrize(
    "page", ["app/web/api.html", "app/web/index.html", "docs/DESIGN.md"]
)
def test_no_page_still_quotes_the_pre_credential_estimate(page: str) -> None:
    """The estimate that was wrong, in the exact forms it was written in."""
    text = (ROOT / page).read_text(encoding="utf-8")
    for stale in ("40-120", "40\u2013120"):
        assert stale not in text, (
            f"{page} still quotes the pre-credential estimate {stale!r}; "
            "the measured range is 225-430s, median 383s"
        )
