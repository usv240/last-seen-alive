"""Does this candidate actually name a moving-image work?

Measured defect, not a hypothetical one. Across the first 19 recorded runs of
the development split, **seven** put something into the candidate slot that is not a
film: a production company (`Bray Studios Inc.`), a physical element of the print
(`black_film_leader`), a restatement of the input (`An unidentified film
fragment`), the fragment's own visuals (`fragment_D03_visuals`), and two costume
or subject-heading clusters. The schema asked for a candidate identity and got
whatever noun phrase the compiler had most evidence for.

Each of those is a real research result and some are useful -- knowing the studio
is genuinely progress -- but none is an identification, and letting them occupy
the candidate slot corrupts every number computed downstream. A costume cluster
cannot be right or wrong about which film this is.

So candidates are type-checked by deterministic code before the gate sees them,
in the same spirit as everything else here: the model proposes, code disposes,
and every rejection carries a reason a human can read and dispute. Rejected
candidates are not deleted -- they are returned in `rejected` so the archivist
still learns the studio was identified.

The rules are conservative on purpose. A wrongly rejected candidate costs recall
on a case that was probably going to need human review anyway; a wrongly accepted
one puts a non-film in front of an archivist as though it were an answer. The
known cost of that choice: a real film actually titled *Fragments*, or a company
name used as a title, would be rejected here. That is a recall loss on a case
already destined for human review, and it is the trade this module chooses.
"""

from __future__ import annotations

import re

#: Words that mark the phrase as an organisation rather than a work, anchored to
#: the end of the string. A studio is the most common non-work this pipeline
#: produces, because trade sources name the studio far more often than they name
#: a one-reel picture. Anchoring keeps "The Company She Keeps" a film.
_ORGANISATION = re.compile(
    r"\b(studios?|inc|incorporated|ltd|limited|llc|company|co|corp|corporation|"
    r"productions?|manufacturing|mfg|"
    r"archives?|museum|library|collection|filmmuseum|cinematheque)\b\.?$",
    re.I,
)

#: Institutions, in the phrase-shapes they actually take. Kept separate from
#: _ORGANISATION because an institution's giveaway word is rarely last: "Library
#: of Congress National Screening Room" ends in "Room". Matched as phrases rather
#: than bare words so that a film called "Museum Hours" survives.
_INSTITUTION = re.compile(
    r"\b(?:"
    r"(?:library|museum|institute|archive|cinematheque|filmmuseum|foundation|"
    r"society|association|federation|university|college)\s+(?:of|for)\b"
    r"|screening\s+room\b"
    r"|national\s+(?:archive|library|film\s+(?:board|registry|preservation))\b"
    r"|moving\s+image\s+(?:archive|collection)\b"
    r"|special\s+collections?\b"
    r")",
    re.I,
)

#: Phrases that restate the input instead of naming a work.
_RESTATEMENT = re.compile(
    r"\b(unidentified|unknown|untitled|no\s+title|fragment|footage|clip|reel|"
    r"visuals?|excerpt|sequence|material)\b",
    re.I,
)

#: Physical or laboratory elements of a print. Real observations, not works.
_FILM_ELEMENT = re.compile(
    r"\b(leader|academy\s+leader|countdown|head\s+leader|edge\s+code|"
    r"perforation|splice|emulsion|nitrate\s+stock|film\s+stock|"
    r"black\s+frame|blank\s+frame)\b",
    re.I,
)

#: Subject headings and descriptive clusters, in the form archives use to
#: describe material they cannot identify. These read like catalogue entries and
#: are easy to mistake for titles.
_DESCRIPTIVE = re.compile(
    r"\b(attire|costume|clothing|workwear|fashion|garment|"
    r"subjects?|scenes?\s+of|views?\s+of|studies\s+of|"
    r"early\s+to\s+mid|late\s+\d{2}th|\d{2}th\s+century|ca\.\s*\d{4})\b",
    re.I,
)

#: A work's title is a name, not a sentence. Compilers that drift into
#: description produce long phrases with connectives.
MAX_TITLE_WORDS = 12
_SENTENCE_LIKE = re.compile(r"\b(and|or|from|with|showing|depicting|featuring|including)\b", re.I)

#: Checked in order. The first rule that fires is the one reported, so the most
#: specific rules come first and the reader gets the most informative reason.
_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "restates_the_input",
        _RESTATEMENT,
        "describes the fragment rather than naming a work",
    ),
    (
        "physical_element",
        _FILM_ELEMENT,
        "names part of the print, not the film on it",
    ),
    (
        "institution",
        _INSTITUTION,
        "names an archive, library or collection. It may well be where the fragment is held, "
        "which is worth recording, but it is not the work",
    ),
    (
        "organisation",
        _ORGANISATION,
        "names a company, not a work. Identifying the studio is a real result, but it is not "
        "an identification",
    ),
    (
        "descriptive_cluster",
        _DESCRIPTIVE,
        "is a subject or costume description of the kind archives use for material they "
        "cannot identify",
    ),
)


def classify(title: str, *, year: str = "") -> tuple[bool, str]:
    """Return (names_a_work, reason).

    `reason` is empty when the candidate is accepted, and otherwise says which
    rule rejected it, so a dossier can show the archivist what was set aside.
    """
    text = (title or "").strip()
    if not text:
        return False, "empty_title: no candidate title was given"

    collapsed = re.sub(r"\s+", " ", text)

    for name, pattern, explanation in _RULES:
        if pattern.search(collapsed):
            return False, f"{name}: {collapsed!r} {explanation}"

    words = collapsed.split()
    if len(words) > MAX_TITLE_WORDS:
        return False, (
            f"too_long: a title of {len(words)} words is a description, not a name "
            f"(limit {MAX_TITLE_WORDS})"
        )
    if _SENTENCE_LIKE.search(collapsed) and len(words) > 6:
        return False, f"sentence_like: {collapsed!r} reads as a description rather than a title"

    return True, ""


def names_a_work(title: str, *, year: str = "") -> bool:
    accepted, _ = classify(title, year=year)
    return accepted
