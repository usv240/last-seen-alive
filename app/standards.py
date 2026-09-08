"""Conformance to published archival cataloguing standards, as data.

The strongest evidence for a tool like this is an archivist using it and saying
what is wrong. We do not have that. This is the next best thing that can be
checked: the requirements are quoted from primary sources with page numbers, and
each one has a test that passes or fails against real output.

It is deliberately not a scorecard. Two requirements are only partially met and
one was failing outright until this exercise ran; all three say so.

See docs/STANDARDS-CONFORMANCE.md for the full quotations and reasoning.
"""

from __future__ import annotations

from typing import Any

SOURCES: list[dict[str, str]] = [
    {
        "id": "fiaf",
        "title": "The FIAF Moving Image Cataloguing Manual",
        "author": "Linda Tadic (ed.)",
        "publisher": "International Federation of Film Archives",
        "year": "2016",
        "url": "https://www.fiafnet.org/pages/E-Resources/Cataloguing-Manual.html",
    },
    {
        "id": "en15907",
        "title": "EN 15907:2010, Film identification: enhancing interoperability of metadata",
        "author": "CEN",
        "publisher": "European Committee for Standardization",
        "year": "2010",
        "url": "https://filmstandards.org/fsc/index.php/EN_15907",
    },
]

REQUIREMENTS: list[dict[str, Any]] = [
    {
        "id": "R1",
        "requirement": "Every statement in a record must derive from a source.",
        "quote": "Information entered in a record must be derived from a source.",
        "citation": "FIAF Manual, §3 Sources of Information, p. 12",
        "also": "EN 15907 provides a dedicated `Record Source` element.",
        "status": "conforms",
        "how": (
            "The citation registry discards any URL Parallel did not return during the run, and "
            "a claim with no surviving verified source cannot carry a threshold. Unsupported "
            "claims are shown to the archivist rather than hidden."
        ),
        "tests": [
            "test_r1_every_decisive_claim_carries_a_source",
            "test_r1_a_claim_without_a_source_cannot_carry_a_threshold",
            "test_r1_every_source_records_where_it_came_from",
        ],
    },
    {
        "id": "R2",
        "requirement": "Cite each individual source in a consistently applied style.",
        "quote": (
            "Cite each individual source of information using an agreed upon, consistently "
            "applied citation style, such as The Chicago Manual of Style, or other style guide."
        ),
        "citation": "FIAF Manual, §3, p. 12",
        "status": "partial",
        "how": (
            "Every source is a structured record: URL, host, verbatim excerpt, retrieval "
            "provider and id, timestamp, and two verification states, applied identically. It "
            "is consistent and machine-readable, but it is not a citation style a cataloguer "
            "could paste into a record. Producing Chicago-style strings alongside would conform "
            "fully; the system does not."
        ),
        "tests": ["test_r2_every_source_has_the_same_structured_shape"],
    },
    {
        "id": "R3",
        "requirement": "Begin with what the supplied source says; correct only on evidence.",
        "quote": (
            "Begin with what the source of information says and correct it only when it is "
            "known to be ambiguous or erroneous."
        ),
        "citation": "FIAF Manual, p. 15",
        "status": "conforms",
        "how": (
            "A supplied catalogue label is passed into the workflow and the Skeptic looks for "
            "evidence for and against it. The Tier E benchmark case requires the conflict to be "
            "surfaced, never silently replaced, which is what the control arm did on one run."
        ),
        "tests": [
            "test_r3_a_supplied_label_reaches_the_workflow",
            "test_r3_the_benchmark_requires_contradiction_not_replacement",
        ],
    },
    {
        "id": "R4",
        "requirement": "Where several identifications are possible, name them all and qualify the uncertainty.",
        "quote": (
            "if the Agent could be one of two or more possibilities then name them and qualify "
            "that there is uncertainty as to which is correct."
        ),
        "citation": "FIAF Manual, p. 147",
        "status": "conforms",
        "how": (
            "This is the `candidates` verdict: every possibility named with its evidence score, "
            "returned with the reason the probable-identity gate did not pass. Two of the ten "
            "benchmark cases require it and treat a single confident answer as a failure."
        ),
        "tests": [
            "test_r4_candidates_verdict_names_all_of_them_with_the_uncertainty",
            "test_r4_the_benchmark_requires_this_behaviour_and_scores_it",
        ],
    },
    {
        "id": "R5",
        "requirement": "An unidentifiable entity still needs a supplied/devised title.",
        "quote": (
            "Supplied/Devised titles are implemented for: […] moving image entities that are "
            "unidentifiable. […] Where possible, use a Title + Title Type approach. This "
            "approach effectively removes the need for brackets by establishing the Title is "
            "supplied/devised by the cataloguer."
        ),
        "citation": "FIAF Manual, §A.2.5, pp. 93–94",
        "status": "was_failing_now_conforms",
        "how": (
            "This is what the exercise found. An abstention used to return no title at all, "
            "leaving the archivist a fragment they could not file, search for or refer to: the "
            "precise problem A.2.5 exists to solve. `app/devised_title.py` now returns a title "
            "on every abstain and candidates verdict, built to the five-Ws pattern, assembled by "
            "deterministic code from observed clues only, and marked "
            "`title_type: supplied_devised` so it can never be read as authoritative."
        ),
        "tests": [
            "test_r5_abstention_still_produces_a_filable_title",
            "test_r5_a_devised_title_is_marked_as_supplied_not_authoritative",
            "test_r5_a_devised_title_follows_the_five_ws_pattern",
            "test_r5_a_devised_title_never_names_a_film",
            "test_r5_the_runtime_attaches_a_devised_title_when_it_cannot_identify",
        ],
    },
    {
        "id": "R6",
        "requirement": "Uncertainty must be explicit, never implied by omission.",
        "quote": (
            "Optionally, when the role performed by an Agent is probable but not certain, "
            "provide the function name followed by a question mark. […] If the relationship is "
            "ambiguous, use a value to indicate this, for example, 'unknown'."
        ),
        "citation": "FIAF Manual, p. 63; precision qualifiers at §2.3.5.1–2.3.5.2, pp. 58–59",
        "status": "conforms",
        "how": (
            "By a different mechanism. Not question-mark notation but an explicit verdict enum, "
            "all nine thresholds returned with their booleans, and a three-state citation audit "
            "where null means not audited and is distinguishable from false, audited and absent."
        ),
        "tests": [
            "test_r6_verdict_is_an_explicit_enum_never_an_absence",
            "test_r6_unaudited_is_distinguishable_from_audited_and_failed",
            "test_r6_an_unmeasured_result_says_so_rather_than_showing_zero",
        ],
    },
    {
        "id": "R7",
        "requirement": "Separate the Work from the carrier: Work / Variant / Manifestation / Item.",
        "quote": "EN 15907 defines Cinematographic Work, Variant, Manifestation and Item.",
        "citation": "EN 15907:2010",
        "status": "partial",
        "how": (
            "We reason about candidate Works and the Item in hand, but emit no four-level record "
            "and model neither Variants nor Manifestations. A fragment that is a variant cut of "
            "a known work would be described as a candidate for the work, with no way to say "
            "'this is the Italian release version'. Recorded so the gap is documented rather "
            "than discovered."
        ),
        "tests": [],
    },
]

DISCLAIMER = (
    "No archivist has reviewed this system. Conformance to the standards archivists work to is "
    "weaker evidence than a practitioner review and is not offered as a substitute for one. "
    "These standards govern how a record should be written; they say nothing about whether the "
    "evidence gathered is the evidence an archivist would have wanted, or whether the seven "
    "thresholds are set anywhere near the right level."
)


def conformance_report() -> dict[str, Any]:
    counts: dict[str, int] = {}
    for item in REQUIREMENTS:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    return {
        "disclaimer": DISCLAIMER,
        "sources": SOURCES,
        "requirements": REQUIREMENTS,
        "counts": counts,
        "tested_by": "tests/test_standards_conformance.py",
        "document": "docs/STANDARDS-CONFORMANCE.md",
    }
