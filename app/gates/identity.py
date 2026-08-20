"""The identity verdict is deterministic and always requires an archivist."""

from __future__ import annotations

from collections import defaultdict
from typing import Mapping, Sequence

from agentic_core.evidence import Claim
from agentic_core.gate import Candidate, GateResult


class IdentityGate:
    def __init__(self, *, candidate_floor: float = 0.35) -> None:
        self.candidate_floor = candidate_floor

    def evaluate(
        self,
        claims: Sequence[Claim],
        context: Mapping[str, object],
    ) -> GateResult:
        candidates = tuple(context.get("candidates", ()))
        if not all(isinstance(candidate, Candidate) for candidate in candidates):
            raise TypeError("context candidates must contain Candidate records")

        decisive_ids = {
            claim_id for candidate in candidates for claim_id in candidate.decisive_claim_ids
        }
        decisive = [claim for claim in claims if claim.claim_id in decisive_ids]
        domains = {domain for claim in decisive for domain in claim.independent_domains}
        clue_families = {
            str(family)
            for family in context.get("decisive_clue_families", ())
            if str(family).strip()
        }
        contradictions_by_subject: dict[str, int] = defaultdict(int)
        for claim in claims:
            if claim.stance == "contradicts" and claim.is_decisive_eligible:
                contradictions_by_subject[claim.subject] += 1

        leading = max(candidates, key=lambda candidate: candidate.score, default=None)
        unresolved_contradictions = (
            contradictions_by_subject.get(leading.candidate_id, 0) if leading else 0
        )
        thresholds = {
            "independent_source_domains>=3": len(domains) >= 3,
            "distinct_clue_families>=2": len(clue_families) >= 2,
            "temporal_compatibility": context.get("temporal_compatibility") is True,
            "entity_compatibility": context.get("entity_compatibility") is True,
            "unresolved_contradictions==0": unresolved_contradictions == 0,
            "every_decisive_claim_has_source": bool(decisive)
            and all(claim.is_decisive_eligible for claim in decisive),
            "human_approved": context.get("human_approved") is True,
        }

        if leading and all(thresholds.values()):
            return GateResult(
                verdict="probable",
                reason="Every evidence and human-review threshold passed.",
                thresholds=thresholds,
                candidates=candidates,
                requires_human=False,
            )
        if leading and leading.score >= self.candidate_floor:
            failed = ", ".join(name for name, passed in thresholds.items() if not passed)
            return GateResult(
                verdict="candidates",
                reason=f"Evidence remains below the probable-identity gate: {failed}.",
                thresholds=thresholds,
                candidates=candidates,
                requires_human=True,
            )
        return GateResult(
            verdict="abstain",
            reason="No candidate reached the minimum evidence floor.",
            thresholds=thresholds,
            candidates=candidates,
            requires_human=True,
        )

