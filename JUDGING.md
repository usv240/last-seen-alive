# Judge path

## Stage-one viability

- Track: Parallel.
- Google ADK/Gemini and the public product are live.
- Mandatory Parallel Search runtime is **not eligible yet**: `/health/integrations` reports `credential_not_configured` until the sponsor credential is attached through Secret Manager.
- Five development and five sealed holdout fragments are hashed and physically separated. Holdout routes return HTTP 423 before reading a file.

## Four equal judging criteria

| Criterion | Strongest proof | Remaining proof needed |
|---|---|---|
| Technological Implementation | Four-role ADK workflow, typed claims, deterministic IdentityGate, sealed evaluation controls | Live Search and Task responses from the real Parallel account |
| Design | No-signup judge key, evidence dossier, explicit abstention | Re-run the complete visible workflow after Parallel activation |
| Potential Impact | Evidence-first archive triage and zero false-confident-ID target | Independent archivist review and honest frozen holdout result |
| Quality of Idea | Multimodal clue extraction plus adversarial historical research, not screenshot similarity | Preserve prior-art scope and report multilingual coverage gaps |

## Required activation order

1. Attach `last-seen-alive-parallel-api-key` from Secret Manager; never expose it to the UI or repository.
2. Make five development cases pass through Search v1 and Task v1.
3. Commit and sign `eval-freeze-*`.
4. Run the five holdouts exactly once and commit all misses.
5. Only then record the public demo.

An abstention is a correct product outcome. The system is triage support, not an archival attribution authority.
