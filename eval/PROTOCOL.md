# Evaluation Protocol v2

## Isolation

The agent receives only the anonymous fragment, case ID, optional `provided_label`, the prediction schema, Gemini, and live Parallel research. It cannot access this repository, the builder, filenames outside the isolated input directory, media metadata, LOC item IDs, or the answer key.

Development cases D01–D05 may be used to tune. Holdout cases H01–H05 may be run only after an `eval-freeze` Git tag exists and the harness records the corpus hash in its durable taint ledger. No retry is permitted after a semantic failure; infrastructure failures must be documented and may be retried only if no model output was produced.

## Frozen budgets

Before the first holdout, record the Gemini model ID, prompt hashes, agent topology, gate thresholds, maximum Parallel searches, maximum opened domains, request timeout, Gemini-call maximum, and dollar-cost ceiling. The intended first pass is 12 searches, 20 opened pages, 180 seconds, and one transport retry.

## Decision contract

- `identified`: exact title/year claim. Allowed only when every identity-gate threshold passes.
- `candidates`: up to three ranked candidates. Required for Tier C ambiguity traps.
- `abstain`: evidence is insufficient. Required for Tier D.
- `contradicted`: the provided catalogue label conflicts with stronger evidence. Required for Tier E.

Every response also contains `gate.passed`, `gate.failed`, claim-level citations with supporting excerpts, contradictions considered, research coverage, limitations, latency, search count, model-call count, and estimated cost.

## Success criteria

The headline metric is false confident identifications; target zero. The holdout gate is at least three of five correct exact or defensible top-three outcomes, zero false confident identifications, correct abstention on the Tier D case, no fabricated citations, and at least one case materially improved by multi-hop historical research over Gemini-without-search.

Report exact/title recall and decision-class accuracy separately. A system that recognizes a Tier C title but emits `identified` has failed that case.
