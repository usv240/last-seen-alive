"""Turn compiled evidence into gate input, dropping anything Parallel did not return.

This is the step that makes the identity gate mean something. It takes the
compiler's typed output and converts it into the immutable Claim/Source records
the gate counts -- but only after checking each citation against what the
Parallel tools actually retrieved during this investigation.

Three things are enforced here rather than asked for in a prompt:

  1. A source whose URL never appeared in a Parallel response is discarded.
  2. A source whose excerpt does not appear in the retrieved text is marked
     unverified, and unverified sources cannot make a claim decisive.
  3. A claim left with no surviving source cannot be decisive, so it cannot
     contribute an independent domain or clue family to the gate.

The result is that a fabricated citation cannot raise the verdict. It can only
lower it, by leaving a candidate with less support than the model asserted.
"""

from __future__ import annotations

from typing import Any

from agentic_core.evidence import Claim, Source, stable_claim_id
from agentic_core.gate import Candidate
from app.evidence_schema import CompiledEvidence
from app.partners.citation_registry import CitationRegistry


class BuiltEvidence:
    """Gate-ready evidence plus a record of what was rejected and why."""

    def __init__(
        self,
        *,
        claims: list[Claim],
        candidates: tuple[Candidate, ...],
        clue_families: set[str],
        rejected: list[dict[str, str]],
        compiled: CompiledEvidence,
    ) -> None:
        self.claims = claims
        self.candidates = candidates
        self.clue_families = clue_families
        self.rejected = rejected
        self.compiled = compiled

    def gate_context(self, *, human_approved: bool = False) -> dict[str, Any]:
        return {
            "candidates": self.candidates,
            "decisive_clue_families": tuple(sorted(self.clue_families)),
            "temporal_compatibility": self.compiled.temporal_compatibility,
            "entity_compatibility": self.compiled.entity_compatibility,
            "human_approved": human_approved,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidates": [
                {
                    "candidate_id": candidate.candidate_id,
                    "label": candidate.label,
                    "score": candidate.score,
                    "decisive_claim_ids": list(candidate.decisive_claim_ids),
                }
                for candidate in self.candidates
            ],
            "claims": [
                {
                    "claim_id": claim.claim_id,
                    "claim_text": claim.claim_text,
                    "subject": claim.subject,
                    "stance": claim.stance,
                    "agent_id": claim.agent_id,
                    "confidence_basis": claim.confidence_basis,
                    "decisive_eligible": claim.is_decisive_eligible,
                    "sources": [
                        {
                            "url": source.url,
                            "domain": source.domain,
                            "excerpt": source.excerpt,
                            "verified": source.verified,
                            "live_verified": source.live_verified,
                            "counts_toward_gate": Claim._counts(source),
                        }
                        for source in claim.sources
                    ],
                }
                for claim in self.claims
            ],
            "clue_families": sorted(self.clue_families),
            "rejected_citations": self.rejected,
            "unresolved_questions": list(self.compiled.unresolved_questions),
            "citation_policy": "a source not returned by Parallel in this run is discarded",
        }


def build(compiled: CompiledEvidence, registry: CitationRegistry) -> BuiltEvidence:
    rejected: list[dict[str, str]] = []
    claims: list[Claim] = []
    family_by_claim: dict[str, str] = {}

    for item in compiled.claims:
        sources: list[Source] = []
        for candidate_source in item.sources:
            retrieved = registry.lookup(candidate_source.url)
            if retrieved is None:
                rejected.append(
                    {
                        "url": candidate_source.url,
                        "reason": "not_returned_by_parallel_in_this_run",
                        "claim": item.claim_text[:160],
                    }
                )
                continue
            verified = registry.supports_excerpt(candidate_source.url, candidate_source.excerpt)
            if not verified:
                rejected.append(
                    {
                        "url": candidate_source.url,
                        "reason": "excerpt_not_found_in_retrieved_text",
                        "claim": item.claim_text[:160],
                    }
                )
            live = registry.live_audit_state(candidate_source.url)
            if live is False:
                rejected.append(
                    {
                        "url": candidate_source.url,
                        "reason": "quoted_text_absent_from_live_page",
                        "claim": item.claim_text[:160],
                    }
                )
            excerpt = candidate_source.excerpt.strip() or (
                retrieved.excerpts[0] if retrieved.excerpts else retrieved.url
            )
            try:
                sources.append(
                    Source(
                        url=retrieved.url,
                        domain=retrieved.domain,
                        excerpt=excerpt[:1200],
                        verified=verified,
                        live_verified=live,
                    )
                )
            except ValueError as exc:
                rejected.append(
                    {"url": candidate_source.url, "reason": f"invalid_source:{exc}", "claim": item.claim_text[:160]}
                )

        # An unverified excerpt is kept for a human to read but must not be able
        # to satisfy the gate, so only verified sources travel with the claim.
        # A source that failed the live Extract audit is deliberately kept here
        # rather than dropped: Claim.is_decisive_eligible refuses to count it,
        # and the archivist should be able to see what did not hold up.
        verified_sources = tuple(source for source in sources if source.verified)
        claim_id = stable_claim_id(item.subject, item.clue_family, item.claim_text)
        try:
            claim = Claim(
                claim_id=claim_id,
                claim_text=item.claim_text,
                subject=item.subject,
                agent_id="EvidenceCompiler",
                stance=item.stance,
                sources=verified_sources or tuple(sources),
                confidence_basis=item.confidence_basis or "compiled from cited research output",
            )
        except ValueError as exc:
            rejected.append({"url": "", "reason": f"invalid_claim:{exc}", "claim": item.claim_text[:160]})
            continue
        claims.append(claim)
        family_by_claim[claim_id] = item.clue_family

    decisive_ids = {claim.claim_id for claim in claims if claim.is_decisive_eligible}

    candidates: list[Candidate] = []
    for entry in compiled.candidates:
        supporting = [
            claim.claim_id
            for claim in claims
            if claim.subject == entry.candidate_id
            and claim.stance == "supports"
            and claim.claim_id in decisive_ids
        ]
        candidates.append(
            Candidate(
                candidate_id=entry.candidate_id,
                label=entry.title if not entry.year else f"{entry.title} ({entry.year})",
                score=entry.score,
                decisive_claim_ids=tuple(supporting),
            )
        )

    leading = max(candidates, key=lambda item: item.score, default=None)
    clue_families = {
        family_by_claim[claim_id]
        for claim_id in (leading.decisive_claim_ids if leading else ())
        if claim_id in family_by_claim
    }

    return BuiltEvidence(
        claims=claims,
        candidates=tuple(candidates),
        clue_families=clue_families,
        rejected=rejected,
        compiled=compiled,
    )
