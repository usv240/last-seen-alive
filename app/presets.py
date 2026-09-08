"""The public demo corpus: what a visitor can watch, download, and run.

Ten 50-second fragments cut from Library of Congress National Screening Room
items, all published by 1929 and in the United States public domain. Five are
development cases anyone may run; five are sealed holdouts that stay unopened
until the implementation is frozen and tagged.

Two things are deliberate here.

The public description of each case says what the case *tests*, not what is in
it. The raw manifest already publishes tier and expected decision class, because
this benchmark measures calibrated behaviour and hiding that would make the
results unreadable. But the manifest's internal `selection_basis` quotes the
exact intertitle for some cases, and putting that on the page would let a viewer
read the answer off the site and then watch the agent "discover" it. So the site
gets a written description of the challenge; the manifest stays downloadable in
full for anyone who wants to check that we did not move the goalposts.

The sealed split is listed rather than hidden. A judge should be able to see
that five cases exist, that their hashes are published, and that the media
endpoint refuses to serve them.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

EVAL_DIR = Path(__file__).resolve().parents[1] / "eval"
MANIFEST = EVAL_DIR / "manifest.json"

LOC_CREDIT = "Library of Congress, Motion Picture, Broadcasting, and Recorded Sound Division."
LOC_RIGHTS_URL = (
    "https://www.loc.gov/collections/national-screening-room/about-this-collection/"
    "rights-and-access/"
)

TIER_NAMES: dict[str, str] = {
    "A": "Rare intertitle",
    "B": "Distinctive visual",
    "C": "Ambiguity trap",
    "D": "Insufficient evidence",
    "E": "Historical misattribution",
}

OUTCOME_NAMES: dict[str, str] = {
    "identify": "Probable identity",
    "candidates": "Ranked candidates only",
    "abstain": "Abstain",
    "contradict": "Contradict the supplied label",
}

#: Written for the public site. Says what the case is *for* without quoting the
#: discriminating evidence the workflow is supposed to find for itself.
PUBLIC_NOTES: dict[str, dict[str, str]] = {
    "D01": {
        "headline": "A dark interior with nothing legible in it.",
        "challenge": (
            "No title card, no signage, no readable text of any kind. There is nothing here "
            "for a phrase search to grip."
        ),
        "why_it_matters": (
            "This is the case a confident system fails. The only correct behaviour is to "
            "abstain and say why. An archivist who is handed a guess here has been actively "
            "misled."
        ),
    },
    "D02": {
        "headline": "One unusual line of dialogue, and a studio mark.",
        "challenge": (
            "A single verbatim intertitle phrased oddly enough to be worth searching literally, "
            "plus a producer's mark in the frame."
        ),
        "why_it_matters": (
            "The best case for the method: exact-phrase retrieval against digitised historical "
            "text, corroborated by a second, independent kind of clue."
        ),
    },
    "D03": {
        "headline": "Generic period action that fits several films at once.",
        "challenge": (
            "Recognisable setting and period, no text, and a scene staged the way dozens of "
            "contemporaneous films staged it."
        ),
        "why_it_matters": (
            "The trap is that a plausible title is easy to produce and impossible to justify. "
            "Ranked candidates with their evidence is the honest answer; a verdict is not."
        ),
    },
    "D04": {
        "headline": "A premise strange enough to be searchable, with no title card.",
        "challenge": (
            "Nothing readable, but an unusual thing happening in an identifiable place and "
            "period: the sort of detail a contemporary review would have mentioned."
        ),
        "why_it_matters": (
            "Tests whether visual description can be turned into a productive text query at "
            "all, which is where most screenshot matchers stop."
        ),
    },
    "D05": {
        "headline": "A catalogue label that the record itself contradicts.",
        "challenge": (
            "This fragment arrives already labelled, the way real archive material does. The "
            "supplied title is one the Library of Congress records as a former, superseded "
            "title for the work."
        ),
        "why_it_matters": (
            "Inherited metadata is how a catalogue error propagates for decades. The required "
            "behaviour is to surface the conflict with evidence, not to accept the label and "
            "not to silently overwrite it."
        ),
    },
}

HOLDOUT_NOTE = (
    "Sealed. Its SHA-256 is published so the file cannot be swapped later. It is opened "
    "exactly once, after the implementation is tagged eval-freeze-*, and every miss is "
    "published with the successes."
)


@lru_cache(maxsize=1)
def _manifest() -> list[dict[str, Any]]:
    return json.loads(MANIFEST.read_text(encoding="utf-8-sig"))


def _public_record(item: dict[str, Any]) -> dict[str, Any]:
    case_id = item["case_id"]
    is_dev = item["split"] == "dev"
    notes = PUBLIC_NOTES.get(case_id, {})
    record: dict[str, Any] = {
        "case_id": case_id,
        "split": item["split"],
        "runnable": is_dev,
        "tier": item["tier"],
        "tier_name": TIER_NAMES.get(item["tier"], item["tier"]),
        "expected_outcome": item["expected_outcome"],
        "expected_outcome_name": OUTCOME_NAMES.get(
            item["expected_outcome"], item["expected_outcome"]
        ),
        "provided_label": item.get("provided_label"),
        "media_type": item["media_type"],
        "duration_seconds": item["duration_seconds"],
        "bytes": item["bytes"],
        "sha256": item["sha256"],
        "transforms": list(item.get("transforms", ())),
        "credit": LOC_CREDIT,
        "rights": "United States public domain; published by 1929.",
        "rights_url": LOC_RIGHTS_URL,
    }
    if is_dev:
        record.update(
            {
                "headline": notes.get("headline", ""),
                "challenge": notes.get("challenge", ""),
                "why_it_matters": notes.get("why_it_matters", ""),
                "media_url": f"/v1/presets/{case_id}/media",
                "download_url": f"/v1/presets/{case_id}/media?download=1",
            }
        )
    else:
        record.update(
            {
                "headline": "Held-out case.",
                "challenge": HOLDOUT_NOTE,
                "why_it_matters": (
                    "A benchmark you can re-run until it passes measures nothing. This split "
                    "exists so the published numbers cannot have been tuned against."
                ),
                "media_url": None,
                "download_url": None,
            }
        )
    return record


def list_presets(*, split: str | None = None) -> list[dict[str, Any]]:
    items = _manifest()
    if split:
        items = [item for item in items if item["split"] == split]
    return [_public_record(item) for item in items]


def get_preset(case_id: str) -> dict[str, Any] | None:
    for item in _manifest():
        if item["case_id"] == case_id:
            return item
    return None


def preset_media_path(case_id: str) -> Path | None:
    item = get_preset(case_id)
    if item is None:
        return None
    return EVAL_DIR / item["file"]


def corpus_summary() -> dict[str, Any]:
    items = _manifest()
    tiers: dict[str, int] = {}
    for item in items:
        tiers[item["tier"]] = tiers.get(item["tier"], 0) + 1
    return {
        "status": "corrected_and_sealed",
        "cases": len(items),
        "development": sum(item["split"] == "dev" for item in items),
        "holdout": sum(item["split"] == "holdout" for item in items),
        "tiers": tiers,
        "tier_names": TIER_NAMES,
        "holdout_run": "not_run",
        "source": "Library of Congress National Screening Room",
        "credit": LOC_CREDIT,
        "rights_url": LOC_RIGHTS_URL,
        "manifest_url": "/v1/eval/manifest",
    }
