# Evaluation Protocol v2

## Isolation

The agent receives only the anonymous fragment, case ID, optional `provided_label`, the prediction schema, Gemini, and live Parallel research. It cannot access this repository, the builder, filenames outside the isolated input directory, media metadata, LOC item IDs, or the answer key.

**What "sealed" means here, precisely.** `eval/answer_key/ground_truth.json` is
committed to this public repository and contains the expected titles for the
held-out cases as well as the development ones. Sealed therefore does **not** mean
the answers are secret — anyone can read them, which is deliberate, because a
benchmark whose answers cannot be checked cannot be audited either. It means the
system has never been run against those five fragments, `/v1/identify` refuses
them with HTTP 423, their media is never served, and the run will happen exactly
once after the implementation is tagged. The protection is against tuning on the
held-out set, not against a reader knowing the answers.

Development cases D01–D05 may be used to tune. Holdout cases H01–H05 may be run only after an `eval-freeze` Git tag exists and the harness records the corpus hash in its durable taint ledger. No retry is permitted after a semantic failure; infrastructure failures must be documented and may be retried only if no model output was produced.

## Frozen budgets

Before the first holdout, record the Gemini model ID, prompt hashes, agent topology, gate thresholds, per-surface Parallel call ceilings, request timeout, Gemini-call maximum, and dollar-cost ceiling.

The pipeline now touches five Parallel surfaces on a held-out run, so the budget is stated per surface rather than as a single search count:

| Surface | Ceiling per case | Enforced by |
|---|---:|---|
| Search | 12 calls, 2–5 queries each, `mode=advanced` | agent tool contract in `parallel_research.py` |
| Task | 1 run, `processor=pro-fast` | one call site, Holdings Researcher |
| FindAll | 1 run, `match_limit=12`, `generator=base` | one call site, strongest candidate only |
| Extract | 8 pages | `MAX_AUDITED_URLS` |
| Task Group | 4 runs, `processor=base` | `MAX_FALSIFIED_CANDIDATES` |
| Monitor | 0 | never called during evaluation; it is an archivist action |

Wall clock: 180 seconds standard, 300 seconds in deep mode, and one transport retry. Record the actual per-surface counts from `parallel_retrieval.calls` in the report, not the ceilings.

The held-out run is executed at `depth=deep`, because the falsification fan-out is part of the system being measured. Record that in the freeze.

## Decision contract

- `identified`: exact title/year claim. Allowed only when every identity-gate threshold passes.
- `candidates`: up to three ranked candidates. Required for Tier C ambiguity traps.
- `abstain`: evidence is insufficient. Required for Tier D.
- `contradicted`: the provided catalogue label conflicts with stronger evidence. Required for Tier E.

Every response also contains `gate.passed`, `gate.failed`, claim-level citations with supporting excerpts, contradictions considered, research coverage, limitations, latency, search count, model-call count, and estimated cost.

## Success criteria

The headline metric is false confident identifications; target zero. The holdout gate is at least three of five correct exact or defensible top-three outcomes, zero false confident identifications, correct abstention on the Tier D case, no fabricated citations, and at least one case materially improved by multi-hop historical research over Gemini-without-search.

Report exact/title recall and decision-class accuracy separately. A system that recognizes a Tier C title but emits `identified` has failed that case.
