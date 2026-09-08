"""The identity verdict is deterministic and always requires an archivist.

Nine thresholds. Two of them -- `competing_hypotheses>=2` and
`leading_hypothesis_has_diagnostic_evidence` -- were added after a stability study
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

*Diagnosticity.* Heuer's central and least intuitive claim is that evidence
supporting a favoured hypothesis usually supports its rivals equally well, so
volume of support proves nothing. Only evidence that *discriminates* counts. The
gate therefore requires the leading candidate to hold at least one kind of
decisive evidence that no rival shares.

The first attempt at this second threshold asked whether the leading hypothesis
was the least contradicted, and it was redundant: `unresolved_contradictions==0`
already requires the leading candidate to have none, and a candidate with none
can never be more contradicted than a rival. It could not fail unless another
threshold had already failed. It was replaced rather than kept for the count.

The same failure is documented in current language-model work: Jhaveri, GX-Chen,
Sucholutsky and Choi, 'Failing to Falsify: Evaluating and Mitigating Confirmation
Bias in Language Models' (arXiv:2604.02485), which finds that confirmation bias
in exploratory reasoning "manifests not in how evidence is interpreted, but in
how evidence is *selected*" -- precisely what fourteen agreeing claims about one
unopposed candidate look like.

Known costs, stated plainly. Requiring a rival can suppress a correct lone
answer. It also creates an incentive for the compiler to invent a weak rival to
satisfy the count -- which is why the diagnosticity test is the harder of the
two: a filler candidate with no decisive claims contributes no clue families, so
it cannot make the leading hypothesis look more discriminating. If anything, a
serious rival makes the threshold harder to pass, which is the correct direction
for a bar to move.
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

        # Heuer's diagnosticity, which is the part that actually bites. Evidence
        # that fits the leading hypothesis often fits its rivals just as well,
        # and evidence consistent with everything discriminates nothing. So the
        # leading candidate must hold at least one *kind* of decisive evidence
        # that no rival shares.
        #
        # An earlier version of this threshold asked instead whether the leading
        # hypothesis was the least contradicted. That was dead weight dressed as
        # rigour: `unresolved_contradictions==0` already requires the leading
        # candidate to have none, and a candidate with none is trivially no more
        # contradicted than any rival. It could never fail on its own. Nine
        # thresholds where one can never fire is worse than eight that can.
        rivals = [candidate for candidate in candidates if candidate is not leading]
        families_by_candidate = context.get("decisive_clue_families_by_candidate") or {}
        leading_families = set(
            families_by_candidate.get(leading.candidate_id, ()) if leading else ()
        )
        rival_families: set[str] = set()
        for rival in rivals:
            rival_families |= set(families_by_candidate.get(rival.candidate_id, ()))
        diagnostic = bool(leading_families - rival_families)

        thresholds = {
            "independent_source_domains>=3": len(domains) >= 3,
            "distinct_clue_families>=2": len(clue_families) >= 2,
            "competing_hypotheses>=2": competing,
            "leading_hypothesis_has_diagnostic_evidence": diagnostic,
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

