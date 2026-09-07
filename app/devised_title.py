"""A supplied/devised title for a fragment the evidence could not identify.

Testing this system against the FIAF Moving Image Cataloguing Manual turned up a
requirement it did not meet. FIAF A.2.5 says supplied/devised titles exist
precisely for "moving image entities that are unidentifiable", and that they
"facilitate the discovery and identification of moving images without formal
title". Until now an abstention produced no title at all — which is honest, but
leaves the archivist with a fragment they still cannot file, search or refer to.

So an abstention now also returns a devised title, built to the pattern the
manual recommends (A.2.5, p.94):

    Who/what: persons, events or objects
    What:     activity
    Where:    location
    When:     time period
    Who/what: name of source or collection

Two rules make this safe.

**It is built by code from the typed clues, never generated as prose.** A model
asked to "devise a title" will reach for a real film's title, and a devised title
that happens to name a real work is an identification smuggled in through the
back door. This assembles only observed descriptors.

**It is marked as cataloguer-supplied, not authoritative.** FIAF notes that
brackets have traditionally signalled information taken from outside the item,
and recommends instead: "Where possible, use a Title + Title Type approach. This
approach effectively removes the need for brackets by establishing the Title is
supplied/devised by the cataloguer." Every devised title here carries
`title_type: "supplied_devised"`, so no consumer can mistake it for a title the
work actually bore.

Reference: The FIAF Moving Image Cataloguing Manual (Linda Tadic, ed., FIAF,
2016), A.2.5 Supplied/Devised Titles, pp. 93-96.
"""

from __future__ import annotations

import re
from typing import Any

#: FIAF A.2.5 asks the title to be "descriptive, describing the Work as
#: succinctly as possible". Long strings defeat that and make a catalogue
#: unreadable, so each component is capped.
MAX_COMPONENT_CHARS = 60
MAX_TITLE_CHARS = 180

_PERIOD_HINTS = (
    (re.compile(r"\b(18[0-9]{2}|19[0-2][0-9]|19[3-9][0-9])\b"), None),
    (re.compile(r"\bedwardian\b", re.I), "Edwardian period"),
    (re.compile(r"\bvictorian\b", re.I), "Victorian period"),
    (re.compile(r"\bbelle[ -]epoque\b", re.I), "Belle Epoque"),
    (re.compile(r"\bsilent(?: era| period)?\b", re.I), "silent era"),
)

_FORM_TERMS = (
    ("animation", "Animation"),
    ("animated", "Animation"),
    ("cartoon", "Animation"),
    ("newsreel", "Newsreel"),
    ("actuality", "Actuality"),
    ("documentary", "Documentary"),
    ("interview", "Interview"),
    ("rushes", "Rushes"),
    ("outtake", "Rushes"),
    ("advertisement", "Advertisement"),
    ("trailer", "Trailer"),
    ("home movie", "Home movie"),
)


def _texts(node: Any) -> list[str]:
    """Every string in a nested clue structure, in order."""
    found: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned:
                found.append(cleaned)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)

    walk(node)
    return found


def _pick(clues: Any, *keys: str) -> list[str]:
    """Strings under any of the named keys, at any depth."""
    found: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if str(key).lower() in keys:
                    found.extend(_texts(item))
                else:
                    walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)

    walk(clues)
    return found


def _trim(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" .,;:—-")
    return value[:MAX_COMPONENT_CHARS].strip()


def _period(strings: list[str]) -> str:
    joined = " ".join(strings)
    for pattern, label in _PERIOD_HINTS:
        match = pattern.search(joined)
        if match:
            return label or match.group(0)
    return ""


def _form_term(strings: list[str]) -> str:
    joined = " ".join(strings).lower()
    for needle, term in _FORM_TERMS:
        if needle in joined:
            return term
    return ""


def devise_title(
    visual_clues: Any,
    *,
    collection: str = "",
    fragment_reference: str = "",
) -> dict[str, Any]:
    """Build a FIAF A.2.5 supplied/devised title from observed clues only.

    Returns the title plus the components it was assembled from, so a cataloguer
    can see exactly which observation produced which part of it.
    """
    everything = _texts(visual_clues)

    who = _pick(visual_clues, "subjects", "people", "performers", "characters", "objects")
    what = _pick(visual_clues, "action", "activity", "events", "scene", "content")
    where = _pick(visual_clues, "location", "place", "setting", "architecture", "region")
    when = _pick(visual_clues, "period", "date", "era", "costume_period", "stock_marks")

    components: dict[str, str] = {}
    if who:
        components["who_what"] = _trim(who[0])
    if what:
        components["what_activity"] = _trim(what[0])
    if where:
        components["where"] = _trim(where[0])
    period = _period(when or everything)
    if period:
        components["when"] = _trim(period)
    if collection:
        components["source_collection"] = _trim(collection)

    form = _form_term(everything)

    ordered = [
        components.get("who_what", ""),
        components.get("what_activity", ""),
        components.get("where", ""),
        components.get("when", ""),
        components.get("source_collection", ""),
    ]
    body = ", ".join(part for part in ordered if part)

    if not body:
        # Nothing describable was observed. FIAF still expects a usable handle,
        # so fall back to the reference the fragment arrived with rather than
        # inventing descriptive content that was not seen.
        body = f"Unidentified fragment {fragment_reference}".strip()

    title = f"{body}. {form}" if form else body
    title = title[:MAX_TITLE_CHARS].strip()

    return {
        "title": title,
        # FIAF A.2.5: "use a Title + Title Type approach. This approach
        # effectively removes the need for brackets by establishing the Title is
        # supplied/devised by the cataloguer."
        "title_type": "supplied_devised",
        "authority": "cataloguer_supplied",
        "is_identification": False,
        "pattern": "FIAF A.2.5 five-Ws (who/what, what, where, when, source)",
        "form_term": form,
        "components": components,
        "standard": "The FIAF Moving Image Cataloguing Manual (2016), A.2.5, pp. 93-96",
        "note": (
            "Assembled by deterministic code from observed clues only. It is a finding aid, "
            "not an identification, and names no film."
        ),
    }
