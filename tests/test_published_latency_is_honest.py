"""Every latency the product states must match the latency it measured.

This test exists because of a real defect. The run console's stage timings were
written from an estimate totalling 100 seconds, before a Parallel credential
existed. When the credential was attached the measured median came in at 383
seconds. Nothing failed: the console simply walked through all six stages in
under two minutes and then sat on the last one for four more, with a live clock
ticking. The file's own opening comment says it exists so that a long wait does
not read as a hang, and the stale numbers made it produce precisely that.

It was then wrong a second time, in the other direction. 383s was the median of
one pass over five fragments. Nineteen runs later the median is 299s and the
spread is far wider than one pass suggested. So the console is bound to the
stability study rather than to any single evaluation, and this test fails the
moment the two disagree.

**The outlier rule.** One recorded run took 5,705 seconds and another returned
502. Cloud Run's own request timeout is 900s, so a run that outlives it is a
reliability event, not a latency, and folding it into "typical" would make the
quoted range useless. Runs above the server timeout are therefore excluded from
what the console may promise -- and, because an exclusion rule is exactly the
sort of thing that quietly launders bad news, this file also asserts that the
published report still discloses them.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "eval" / "reports" / "stability.json"
CONSOLE = ROOT / "app" / "web" / "console.js"

#: The stage cadence is a shape, not an instrument, so it does not have to equal
#: the median exactly. It does have to land in the same part of the minute, or
#: the console runs out of stages while the request is still in flight.
TOLERANCE = 0.25

#: Cloud Run's configured request timeout. A run longer than this did not take
#: that long to think; something went wrong.
SERVER_TIMEOUT_SECONDS = 900


@pytest.fixture(scope="module")
def measured() -> dict[str, float]:
    report = json.loads(STUDY.read_text(encoding="utf-8"))
    latencies = sorted(
        observation["latency_seconds"]
        for case in report["results"]
        for observation in case["observations"]
        if observation.get("latency_seconds")
    )
    typical = [value for value in latencies if value <= SERVER_TIMEOUT_SECONDS]
    assert typical, "no run completed inside the server timeout"
    return {
        "median": typical[len(typical) // 2],
        "low": typical[0],
        "high": typical[-1],
        "n": len(typical),
        "excluded": len(latencies) - len(typical),
    }


def _stage_seconds() -> list[int]:
    source = CONSOLE.read_text(encoding="utf-8")
    block = re.search(r"const STAGES = \[(.*?)\n  \];", source, re.S)
    assert block, "STAGES array not found; this test needs updating with the console"
    return [int(match) for match in re.findall(r",\s*(\d+)\],", block.group(1))]


def _constant(name: str) -> int:
    source = CONSOLE.read_text(encoding="utf-8")
    match = re.search(rf"const {name} = (\d+);", source)
    assert match, f"{name} not found in console.js"
    return int(match.group(1))


def test_the_console_walks_for_about_as_long_as_a_run_actually_takes(measured) -> None:
    total = sum(_stage_seconds())
    median = measured["median"]
    assert abs(total - median) <= median * TOLERANCE, (
        f"the console narrates {total}s of work but the median run measures {median:.0f}s. "
        "A viewer watching the last stage for the difference reads it as a hang."
    )


def test_every_stage_has_a_positive_duration() -> None:
    stages = _stage_seconds()
    assert len(stages) == 6, f"expected six named stages, found {len(stages)}"
    assert all(seconds > 0 for seconds in stages), "a zero-length stage is never seen"


def test_the_console_quotes_the_measured_spread(measured) -> None:
    """The up-front estimate must come from the study, not from memory."""
    assert _constant("TYPICAL_LOW") == pytest.approx(measured["low"], abs=5), (
        f"console promises a floor of {_constant('TYPICAL_LOW')}s; "
        f"the fastest measured run was {measured['low']:.0f}s"
    )
    assert _constant("TYPICAL_HIGH") == pytest.approx(measured["high"], abs=5), (
        f"console promises a ceiling of {_constant('TYPICAL_HIGH')}s; "
        f"the slowest run inside the server timeout was {measured['high']:.0f}s"
    )
    assert _constant("TYPICAL_MEDIAN") == pytest.approx(measured["median"], abs=5)


def test_the_console_says_how_many_runs_it_is_quoting(measured) -> None:
    """A median with no n behind it is a number a reader cannot weigh."""
    source = CONSOLE.read_text(encoding="utf-8")
    assert str(measured["n"]) in source, (
        f"the console quotes a median but never says it comes from {measured['n']} runs"
    )


def test_the_excluded_outliers_are_still_published(measured) -> None:
    """An exclusion rule must not be a way to delete the bad runs."""
    if not measured["excluded"]:
        pytest.skip("no run exceeded the server timeout")
    report = json.loads(STUDY.read_text(encoding="utf-8"))
    recorded = [
        observation["latency_seconds"]
        for case in report["results"]
        for observation in case["observations"]
        if observation.get("latency_seconds")
    ]
    assert any(value > SERVER_TIMEOUT_SECONDS for value in recorded), (
        "the console excludes an outlier that the published study no longer contains"
    )
    assert "95 minutes" in CONSOLE.read_text(encoding="utf-8"), (
        "the console excludes a very slow run without telling the reader it happened"
    )


@pytest.mark.parametrize(
    "page", ["app/web/api.html", "app/web/index.html", "docs/DESIGN.md"]
)
def test_no_page_still_quotes_the_pre_credential_estimate(page: str) -> None:
    """The estimate that was wrong, in the exact forms it was written in."""
    text = (ROOT / page).read_text(encoding="utf-8")
    for stale in ("40-120", "40–120"):
        assert stale not in text, (
            f"{page} still quotes the pre-credential estimate {stale!r}; "
            "the measured range is in eval/reports/stability.json"
        )
