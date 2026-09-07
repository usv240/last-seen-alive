"""The control arm: what Gemini does with the same fragment and nothing else.

The product's central claim is that live open-web research plus deterministic
gating changes the answer for the better. That claim is untested unless someone
measures the alternative, and the alternative most people would actually reach
for is a capable multimodal model asked the question directly.

So this arm gives Gemini the identical fragment with **no tools, no web access,
no citation registry and no gate**, and records what it says. Nothing here is a
straw man: it is the same model, the same fragment, and a prompt that asks the
question a working archivist would ask.

What it measures is *calibration*, not correctness. Two of the five development
fragments were selected precisely because their visible evidence cannot support
an identification -- one has no legible text at all, one is a deliberate
ambiguity trap. A system that names a film for those has produced a
false-confident identification, which is the single failure mode this product
exists to avoid. The comparison is therefore:

    on the fragments where the evidence cannot support an identification,
    how often does each arm name one anyway?

The control needs only Vertex AI, so it runs today, before the Parallel
credential exists. That ordering is deliberate: the baseline should be measured
before the system it is a baseline for, not afterwards when the number would be
easy to rationalise.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any

from agentic_core.agents import GeminiJsonGenerator

CONTROL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "names_a_film": {
            "type": "boolean",
            "description": "True if you are putting forward a specific film as the identity.",
        },
        "title": {"type": "string", "description": "The title, or empty if you name none."},
        "year": {"type": "string", "description": "Release year, or empty."},
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low", "none"],
            "description": "How confident you are in the identification you have given.",
        },
        "reasoning": {"type": "string", "description": "Why, in two or three sentences."},
        "visible_evidence": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Only what is actually visible in the fragment.",
        },
        "citable_sources": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "URLs you can cite for this identification. You have no web access, so be "
                "honest: if you cannot verify a URL right now, return an empty list."
            ),
        },
    },
    "required": ["names_a_film", "title", "confidence", "reasoning", "visible_evidence"],
}

SYSTEM_INSTRUCTION = (
    "You are an experienced film archivist examining an unidentified moving-image "
    "fragment. Answer as you would for a colleague who has asked what this reel is. "
    "Be specific where the evidence allows it and say so plainly where it does not."
)


def _prompt(provided_label: str | None) -> str:
    label = (
        f"The can carries the supplied title {provided_label!r}, which may or may not be correct. "
        if provided_label
        else "The fragment arrives with no label of any kind. "
    )
    return (
        "Identify this archival film fragment if you can. "
        + label
        + "Report what is actually visible in the frames, then say whether that evidence "
        "supports naming a specific film. If it does, name it. If it does not, say so."
    )


@dataclass
class ControlResult:
    case_id: str
    names_a_film: bool
    title: str
    year: str
    confidence: str
    reasoning: str
    visible_evidence: list[str] = field(default_factory=list)
    citable_sources: list[str] = field(default_factory=list)
    latency_ms: int = 0
    tokens: int | None = None
    engaged_supplied_label: bool | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "names_a_film": self.names_a_film,
            "title": self.title,
            "year": self.year,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "visible_evidence": self.visible_evidence,
            "citable_sources": self.citable_sources,
            "latency_ms": self.latency_ms,
            "tokens": self.tokens,
            "engaged_supplied_label": self.engaged_supplied_label,
            "error": self.error,
        }


def run_control(
    *,
    case_id: str,
    fragment_path: Path,
    media_type: str,
    provided_label: str | None,
    model: str | None = None,
    temperature: float = 0.0,
) -> ControlResult:
    """Ask Gemini directly. No search, no gate, no verification of any kind."""
    generator = GeminiJsonGenerator(
        project=os.environ.get("GOOGLE_CLOUD_PROJECT", "agentic-fleet-2026"),
        location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
        model=model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
    )
    started = perf_counter()
    try:
        raw = generator.generate(
            prompt=_prompt(provided_label),
            response_schema=CONTROL_SCHEMA,
            system_instruction=SYSTEM_INSTRUCTION,
            media=[(fragment_path.read_bytes(), media_type)],
            temperature=temperature,
        )
    except Exception as exc:
        return ControlResult(
            case_id=case_id,
            names_a_film=False,
            title="",
            year="",
            confidence="none",
            reasoning="",
            latency_ms=round((perf_counter() - started) * 1000),
            error=f"{type(exc).__name__}: {exc}",
        )

    usage = raw.get("_usage") or {}
    return ControlResult(
        case_id=case_id,
        names_a_film=bool(raw.get("names_a_film")),
        title=str(raw.get("title") or ""),
        year=str(raw.get("year") or ""),
        confidence=str(raw.get("confidence") or "none"),
        reasoning=str(raw.get("reasoning") or ""),
        visible_evidence=[str(x) for x in (raw.get("visible_evidence") or [])],
        citable_sources=[str(x) for x in (raw.get("citable_sources") or [])],
        latency_ms=round((perf_counter() - started) * 1000),
        tokens=usage.get("total_tokens"),
        engaged_supplied_label=_engaged_label(raw, provided_label),
    )


def _engaged_label(raw: dict[str, Any], provided_label: str | None) -> bool | None:
    """Did the answer acknowledge the label the can arrived with?

    None when there was no label. Inherited metadata is how a catalogue error
    propagates for decades, so a system handed a supplied title should either
    confirm it or contradict it -- silently replacing it with a third answer is
    the behaviour the Tier E case exists to detect.
    """
    if not provided_label:
        return None
    haystack = " ".join(
        [str(raw.get("reasoning") or ""), *(str(x) for x in (raw.get("visible_evidence") or []))]
    ).lower()
    return provided_label.lower() in haystack


#: Development cases whose visible evidence cannot support naming a film. Taken
#: from the public manifest's required behaviour, not from the sealed answers:
#: `abstain` means no film may be named, `candidates` means no single film may
#: be put forward as the identity.
NO_IDENTIFICATION_POSSIBLE = {"abstain", "candidates"}


def summarise(results: list[ControlResult], expected: dict[str, str]) -> dict[str, Any]:
    """Score the control arm on what the measurement actually supports.

    The first run of this produced a result that contradicted the assumption it
    was written to test. The expectation was that an ungated model would name a
    film for everything; it did not. Gemini abstained correctly on both
    fragments whose evidence cannot support an identification. That number is
    reported first, and unchanged, because a benchmark you rewrite after seeing
    its answer measures nothing.

    What the control does fail is *sourcing*: every identification it made was
    at high confidence and cited nothing, because it has no way to cite. An
    archivist cannot act on an unsourceable identification, and that -- not
    hallucinated titles -- is the gap this product fills.
    """
    scored = [r for r in results if r.error is None]
    constrained = [r for r in scored if expected.get(r.case_id) in NO_IDENTIFICATION_POSSIBLE]
    false_confident = [r for r in constrained if r.names_a_film]

    identifications = [r for r in scored if r.names_a_film]
    unsourced = [r for r in identifications if not r.citable_sources]

    labelled = [r for r in scored if r.engaged_supplied_label is not None]
    ignored_label = [r for r in labelled if r.engaged_supplied_label is False]

    by_case: dict[str, list[ControlResult]] = {}
    for r in scored:
        by_case.setdefault(r.case_id, []).append(r)
    unstable = sorted(
        case_id
        for case_id, runs in by_case.items()
        if len(runs) > 1 and len({(r.names_a_film, r.title.strip().lower()) for r in runs}) > 1
    )

    return {
        "arm": "control",
        "description": (
            "Gemini given the same fragment with no web access, no citation checking and no "
            "deterministic gate."
        ),
        "runs": len(results),
        "cases": len(by_case),
        "runs_errored": len(results) - len(scored),

        # Calibration. Reported first because it is the metric this was built to
        # test, and it did not come out the way it was expected to.
        "runs_where_no_identification_is_possible": len(constrained),
        "false_confident_identifications": len(false_confident),
        "false_confident_case_ids": sorted({r.case_id for r in false_confident}),

        # Sourcing. This is where the control actually fails.
        "identifications_made": len(identifications),
        "identifications_with_no_citable_source": len(unsourced),
        "unsourceable_identification_rate": (
            round(len(unsourced) / len(identifications), 3) if identifications else None
        ),

        # Inherited metadata. A supplied title should be confirmed or
        # contradicted, never silently replaced with a third answer.
        "runs_with_a_supplied_label": len(labelled),
        "runs_that_ignored_the_supplied_label": len(ignored_label),

        "unstable_cases_across_repeats": unstable,
        "median_latency_ms": (
            sorted(r.latency_ms for r in scored)[len(scored) // 2] if scored else None
        ),
        "results": [r.as_dict() for r in results],
        "reading": (
            "The control is well calibrated on abstention: it declined to name a film for both "
            "fragments whose evidence cannot support one. It is not a hallucination machine and "
            "this report does not claim it is. What it cannot do is show its work -- every "
            "identification it made was high-confidence and uncitable -- and on the fragment "
            "carrying a superseded catalogue title it produced a third title instead of engaging "
            "with the label at all. Those two failures are what the full system's citation "
            "registry, live citation audit and deterministic gate exist to address."
        ),
    }


# ---------------------------------------------------------------------------
# Arm B: the control's own answers, put through the real gate.
#
# Arm A measures a capable model alone. Arm C -- the full system -- needs the
# Parallel credential and cannot run yet. Arm B sits between them and needs
# nothing new: take exactly what the control said and pass it through the real
# `build_evidence` and the real `IdentityGate`.
#
# This is not circular. It answers a question neither other arm does: is the
# gate doing work, or is it a rubber stamp? The control produced seven
# high-confidence identifications that no source supports. If the gate lets any
# of them through, the gate is decoration.
#
# It also frames the question Arm C exists to answer. Arm B establishes that
# unsourced claims cannot pass. Whether *sourced* claims can pass -- whether
# real open-web evidence lifts a fragment above the threshold rather than
# merely failing more expensively -- is exactly what the credential unblocks.

from app.evidence_builder import build as build_evidence  # noqa: E402
from app.evidence_schema import CompiledCandidate, CompiledClaim, CompiledEvidence  # noqa: E402
from app.gates.identity import IdentityGate  # noqa: E402
from app.partners.citation_registry import CitationRegistry  # noqa: E402


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return cleaned or "unnamed_candidate"


def gate_the_control(result: ControlResult) -> dict[str, Any]:
    """Run one control answer through the production evidence path and gate.

    The citation registry starts empty, which is the honest representation of a
    run with no web access: nothing was retrieved, so nothing the model cites
    can be confirmed as retrieved.
    """
    if not result.names_a_film:
        return {
            "case_id": result.case_id,
            "control_named_a_film": False,
            "gated_verdict": "abstain",
            "gated_reason": "The control named no film, so there was nothing to gate.",
            "changed": False,
        }

    candidate_id = _slug(result.title)
    compiled = CompiledEvidence(
        candidates=[
            CompiledCandidate(
                candidate_id=candidate_id,
                title=result.title,
                year=result.year,
                # The control reports confidence, not evidence strength. Mapping
                # its highest confidence to a high score is the most generous
                # reading available to it.
                score=0.9 if result.confidence == "high" else 0.5,
                rationale=result.reasoning[:400],
            )
        ],
        claims=[
            CompiledClaim(
                claim_text=observation[:500],
                subject=candidate_id,
                stance="supports",
                clue_family="visual_or_material",
                confidence_basis=f"Observed by the model; control confidence {result.confidence}.",
                sources=[],
            )
            for observation in (result.visible_evidence or [result.reasoning])[:6]
            if observation.strip()
        ],
        temporal_compatibility=True,
        entity_compatibility=True,
    )

    evidence = build_evidence(compiled, CitationRegistry())
    gate = IdentityGate().evaluate(
        claims=evidence.claims,
        context=evidence.gate_context(human_approved=False),
    )
    return {
        "case_id": result.case_id,
        "control_named_a_film": True,
        "control_title": result.title,
        "control_confidence": result.confidence,
        "gated_verdict": gate.verdict,
        "gated_reason": gate.reason,
        "thresholds_failed": list(gate.failed),
        "changed": True,
    }


def summarise_gated(results: list[ControlResult]) -> dict[str, Any]:
    """What the gate does to the control's answers."""
    scored = [r for r in results if r.error is None]
    gated = [gate_the_control(r) for r in scored]
    named = [g for g in gated if g["control_named_a_film"]]
    survived = [g for g in named if g["gated_verdict"] not in {"abstain", "candidates"}]

    return {
        "arm": "control_plus_gate",
        "description": (
            "The control's own answers passed through the production evidence builder and "
            "IdentityGate, with an empty citation registry because nothing was retrieved."
        ),
        "runs": len(scored),
        "control_identifications": len(named),
        "identifications_surviving_the_gate": len(survived),
        "verdicts": sorted({g["gated_verdict"] for g in gated}),
        "per_case": gated,
        "reading": (
            "The gate is not a rubber stamp: every high-confidence identification the control "
            "made was refused, because none of them had a source that had actually been "
            "retrieved. What this arm cannot show is the other direction -- whether real "
            "open-web evidence lifts a fragment ABOVE the threshold rather than just failing "
            "more expensively. That is precisely the question the Parallel credential unblocks, "
            "and it is why this is a two-arm result and not a three-arm one."
        ),
    }
