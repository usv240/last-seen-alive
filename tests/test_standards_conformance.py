"""Conformance to published archival cataloguing standards.

Each test names the requirement it enforces and the primary source it comes
from. See docs/STANDARDS-CONFORMANCE.md for the full quotations, page numbers
and the two places where conformance is only partial.

No archivist has reviewed this system. Testing against the standards archivists
work to is weaker evidence than a practitioner review, but it is real evidence
and it is checkable — and it already caught one requirement (R5) the system was
failing.

Sources:
  FIAF — The FIAF Moving Image Cataloguing Manual, Linda Tadic (ed.),
         International Federation of Film Archives, 2016.
  EN 15907:2010 — Film identification: enhancing interoperability of metadata.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.devised_title import devise_title
from app.example_dossier import worked_example
from app.presets import list_presets

EVAL_DIR = Path(__file__).resolve().parents[1] / "eval"


# ---------------------------------------------------------------- R1: sources
# FIAF p.12: "Information entered in a record must be derived from a source."
# EN 15907 provides a dedicated `Record Source` element for the same purpose.

def test_r1_every_decisive_claim_carries_a_source() -> None:
    evidence = worked_example()["evidence"]
    decisive = [c for c in evidence["claims"] if c["decisive_eligible"]]
    assert decisive, "the example must exercise the decisive path"
    for claim in decisive:
        assert claim["sources"], f"decisive claim with no source: {claim['claim_text'][:60]}"


def test_r1_a_claim_without_a_source_cannot_carry_a_threshold() -> None:
    """An unsupported claim is reported, not hidden — but it counts for nothing."""
    evidence = worked_example()["evidence"]
    unsupported = [c for c in evidence["claims"] if not c["sources"]]
    assert unsupported, "the example must show what an unsupported claim looks like"
    for claim in unsupported:
        assert claim["decisive_eligible"] is False


def test_r1_every_source_records_where_it_came_from() -> None:
    """EN 15907 `Record Source`: the provenance of a statement is part of it."""
    for claim in worked_example()["evidence"]["claims"]:
        for source in claim["sources"]:
            assert source["url"], "a source without a URL has no provenance"
            assert source["domain"], "a source must record its host"
            assert source["excerpt"], "a source must record what it actually said"


# ------------------------------------------------------- R2: citation shape
# FIAF p.12: "Cite each individual source of information using an agreed upon,
# consistently applied citation style."  We diverge: structured, not Chicago.

def test_r2_every_source_has_the_same_structured_shape() -> None:
    """Consistency is the testable half of R2. The style itself is a documented gap."""
    required = {"url", "domain", "excerpt", "verified", "live_verified", "counts_toward_gate"}
    sources = [s for c in worked_example()["evidence"]["claims"] for s in c["sources"]]
    assert sources
    for source in sources:
        assert required <= set(source), f"source is missing {required - set(source)}"


# --------------------------------------------------------- R3: supplied label
# FIAF p.15: "Begin with what the source of information says and correct it only
# when it is known to be ambiguous or erroneous."

def test_r3_a_supplied_label_reaches_the_workflow() -> None:
    """A catalogue title that arrives with the fragment must not be discarded."""
    manifest = json.loads((EVAL_DIR / "manifest.json").read_text(encoding="utf-8-sig"))
    labelled = [row for row in manifest if row.get("provided_label")]
    assert labelled, "the benchmark must include a case that arrives labelled"

    import inspect

    from app import adk_runtime
    from app.adk_runtime import _run_workflow  # noqa: F401  (import proves the path exists)

    source = inspect.getsource(adk_runtime._run_workflow)
    assert "provided_label" in source, "the supplied label must reach the prompt"


def test_r3_the_benchmark_requires_contradiction_not_replacement() -> None:
    """The required behaviour for a false supplied title is `contradict`.

    Not `identify` — silently substituting a different title is the failure mode
    the rule exists to prevent, and is what the control arm did.
    """
    presets = {p["case_id"]: p for p in list_presets()}
    labelled = [p for p in presets.values() if p.get("provided_label")]
    assert labelled
    for preset in labelled:
        assert preset["expected_outcome"] == "contradict", (
            f"{preset['case_id']} arrives labelled but is not required to contradict"
        )


# ------------------------------------------------------------ R4: candidates
# FIAF p.147: "if the Agent could be one of two or more possibilities then name
# them and qualify that there is uncertainty as to which is correct."

def test_r4_candidates_verdict_names_all_of_them_with_the_uncertainty() -> None:
    example = worked_example()
    gate = example["gate"]
    assert gate["verdict"] == "candidates"

    candidates = example["evidence"]["candidates"]
    assert len(candidates) >= 2, "a candidates verdict must name every possibility"
    for candidate in candidates:
        assert candidate["label"], "each possibility must be named"
        assert 0.0 <= candidate["score"] <= 1.0

    # ...and the uncertainty has to be qualified, not merely implied.
    assert gate["reason"], "the verdict must say why it is not an identification"
    assert gate["failed"], "the unmet thresholds are the qualification"
    assert gate["requires_human"] is True


def test_r4_the_benchmark_requires_this_behaviour_and_scores_it() -> None:
    outcomes = {p["case_id"]: p["expected_outcome"] for p in list_presets()}
    assert sum(1 for o in outcomes.values() if o == "candidates") >= 2


# -------------------------------------------------------- R5: devised titles
# FIAF A.2.5 p.93: supplied/devised titles are implemented for "moving image
# entities that are unidentifiable", and p.94 recommends Title + Title Type.
#
# The system was failing this until the conformance exercise ran.

def test_r5_abstention_still_produces_a_filable_title() -> None:
    """Being unable to identify something is no reason to leave it unnameable."""
    devised = devise_title(
        {"notes": ["a dark interior", "no legible text of any kind"]},
        fragment_reference="D01",
    )
    assert devised["title"], "an unidentifiable fragment must still get a title"
    assert "D01" in devised["title"]


def test_r5_a_devised_title_is_marked_as_supplied_not_authoritative() -> None:
    """FIAF p.94: the Title + Title Type approach establishes who supplied it."""
    devised = devise_title({"location": ["a Paris street"]}, fragment_reference="X")
    assert devised["title_type"] == "supplied_devised"
    assert devised["authority"] == "cataloguer_supplied"
    assert devised["is_identification"] is False


def test_r5_a_devised_title_follows_the_five_ws_pattern() -> None:
    devised = devise_title(
        {
            "subjects": ["a young woman"],
            "action": ["lighting a street lamp at dusk"],
            "location": ["a terraced street"],
            "costume_period": ["late Edwardian dress"],
        },
        collection="Library of Congress National Screening Room",
        fragment_reference="D01",
    )
    components = devised["components"]
    assert {"who_what", "what_activity", "where", "when", "source_collection"} <= set(components)
    for value in components.values():
        assert value in devised["title"]


def test_r5_a_devised_title_never_names_a_film() -> None:
    """The place an identification could be smuggled in through the back door.

    A devised title is built by code from observed descriptors. Nothing a model
    wrote as a candidate title may appear in it.
    """
    clues = {
        "subjects": ["a young woman"],
        "candidate_title": ["Bobby Bumps' Night Out"],
        "identification": ["this is certainly The Lamplighter's Daughter"],
    }
    devised = devise_title(clues, fragment_reference="D01")
    assert "bobby bumps" not in devised["title"].lower()
    assert "lamplighter's daughter" not in devised["title"].lower()


def test_r5_the_runtime_attaches_a_devised_title_when_it_cannot_identify() -> None:
    import inspect

    from app import adk_runtime

    source = inspect.getsource(adk_runtime.run_investigation)
    assert "devise_title" in source
    assert "supplied_title" in source
    assert 'gate.verdict in {"abstain", "candidates"}' in source


# ------------------------------------------------------------ R6: uncertainty
# FIAF pp.58-59, 63: uncertainty is recorded explicitly — "unknown", a precision
# qualifier, or a question mark — never left to be inferred from an absence.

def test_r6_verdict_is_an_explicit_enum_never_an_absence() -> None:
    gate = worked_example()["gate"]
    assert gate["verdict"] in {"confirmed", "probable", "candidates", "abstain", "contradicted"}
    assert len(gate["thresholds"]) == 9
    for name, value in gate["thresholds"].items():
        assert isinstance(value, bool), f"{name} is not an explicit boolean"


def test_r6_unaudited_is_distinguishable_from_audited_and_failed() -> None:
    """Three states, not two. `null` means not checked; `false` means checked and absent."""
    sources = [s for c in worked_example()["evidence"]["claims"] for s in c["sources"]]
    states = {s["live_verified"] for s in sources}
    assert True in states, "the example must contain a confirmed citation"
    assert False in states, "the example must contain a refused citation"
    # None is permitted and meaningful; assert the field always exists.
    for source in sources:
        assert "live_verified" in source


def test_r6_an_unmeasured_result_says_so_rather_than_showing_zero() -> None:
    """A metric that has not been run must not be rendered as a value of 0."""
    index = (Path(__file__).resolve().parents[1] / "app" / "web" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "Not run" in index, "unmeasured held-out metrics must be labelled, not zeroed"


def test_r5_a_devised_title_is_never_just_the_collection_name() -> None:
    """Caught in the first live run.

    With no descriptive clues, the title came out as "Library of Congress
    National Screening Room" — true, useless, and identical for every fragment
    in the collection. FIAF A.2.5 asks the title to describe the Work; the
    collection is the last of the five Ws, never the whole of it.
    """
    devised = devise_title(
        {"notes": ["nothing legible"]},
        collection="Library of Congress National Screening Room",
        fragment_reference="D02",
    )
    assert devised["title"] != "Library of Congress National Screening Room"
    assert "D02" in devised["title"], "it must still identify which fragment this is"
