"""The identity verdict is deterministic and always requires an archivist.

Nine thresholds. Two of them -- `competing_hypotheses>=2` and
`leading_hypothesis_least_contradicted` -- were added after a stability study
found the gate could be walked up to five of seven by a single hypothesis that
nothing ever contested. D04 returned the same wrong film in three of four runs,
with fourteen claims all agreeing with it, because the pipeline proposed one
candidate and then researched only that candidate.

Both are Richard Heuer's Analysis of Competing Hypotheses, the structured
analytic technique the CIA adopted for exactly this failure mode (Heuer,
*Psychology of Intelligence Analysis*, 1999; evaluated in Dhami et al., 'The
"analysis of competing hypotheses" in intelligence analysis', *Applied Cognitive
Psychology*, 2019). Two of its steps matter here:

*Consider alternative hypotheses.* A lone hypothesis cannot be assessed at all,
because diagnosticity is a property of a *set*: evidence only discriminates if
there is something for it to discriminate against.

*Judge by inconsistency, not support.* Heuer's central and least intuitive claim
is that evidence supporting a favoured hypothesis usually supports its rivals
equally well, so the hypothesis to prefer is the one with the least inconsistent
evidence rather than the most consistent evidence.

The same failure is documented in current language-model work: Jhaveri, GX-Chen,
Sucholutsky and Choi, 'Failing to Falsify: Evaluating and Mitigating Confirmation
Bias in Language Models' (arXiv:2604.02485), which finds that confirmation bias
in exploratory reasoning "manifests not in how evidence is interpreted, but in
how evidence is *selected*" -- precisely what fourteen agreeing claims about one
unopposed candidate look like.

Known cost, stated plainly: requiring a rival can suppress a correct lone
answer, and it creates an incentive for the compiler to invent a weak rival to
satisfy the count. The second is why the rival must clear the same evidence
bar -- an invented candidate with no sourced claims does not make the leading
one look better, and `leading_hypothesis_least_contradicted` is judged on
contradictions rather than on how many names were listed.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence

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
        # Heuer's first step, and the one this gate was missing. Measured over 19
        # runs, D04 produced exactly one candidate every time and then spent 14
        # claims agreeing with it -- three of four runs converging on the same
        # wrong film at five of seven thresholds. Nothing ever competed with it,
        # so no amount of evidence could discriminate. A hypothesis that was
        # never opposed has not been tested, however much support it accumulated.
        competing = len(candidates) >= 2

        # Heuer's inversion: choose the hypothesis with the *least inconsistent*
        # evidence rather than the most supporting evidence. Supporting evidence
        # is cheap and, as Heuer notes, frequently consistent with every rival
        # too; it is the contradictions that discriminate.
        rivals = [candidate for candidate in candidates if candidate is not leading]
        least_contradicted = bool(leading) and all(
            unresolved_contradictions <= contradictions_by_subject.get(rival.candidate_id, 0)
            for rival in rivals
        )

        thresholds = {
            "independent_source_domains>=3": len(domains) >= 3,
            "distinct_clue_families>=2": len(clue_families) >= 2,
            "competing_hypotheses>=2": competing,
            "leading_hypothesis_least_contradicted": least_contradicted,
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

