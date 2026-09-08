# Submission status

Last verified: 2026-09-07. Full audit: [`docs/AUDIT-2026-09-05.md`](docs/AUDIT-2026-09-05.md).

| Gate | Status | Evidence / next action |
|---|---|---|
| Public standalone repository + Apache-2.0 | Pass | GitHub repository and detected licence. |
| Hosted product | Pass | Cloud Run; four pages, public API, no-signup judge key. |
| Google ADK + Gemini runtime | Pass | `app/adk_runtime.py`; live Vertex health probe. |
| Public demo set, viewable and downloadable | Pass | `/presets`; range-request playback, download, published SHA-256 served as a response header. |
| Bring your own data | Pass | `POST /v1/investigate`; validated before any partner call, held in memory only. |
| Usable as an API by a third party | Pass | Signed stateless keys, key-gated endpoints, stable error contract, live playground at `/api`. |
| All six Parallel surfaces implemented | Pass | Search, Task, FindAll, Extract, Task Group, Monitor. See `/stack`. |
| Sponsor stack visible on every page | Pass | Live ribbon on all four pages, driven by `GET /v1/stack`. |
| Typed evidence into the identity gate | Pass | `EvidenceCompiler` emits a schema; `app/evidence_builder.py` builds Claim/Candidate records. |
| Citations verified against Parallel output | Pass | `app/partners/citation_registry.py`; invented URLs cannot reach a probable verdict. |
| Citations audited against the live page | Pass | Parallel Extract; a source failing the audit cannot carry a threshold. |
| Survival-claim language enforced at runtime | Pass | `find_prohibited_language` runs on every investigation; violations are surfaced, not published. |
| Evidence board UI | Pass | Renderer verified against the worked example at `/v1/example/dossier`, which is built by the real gate. Not yet seen with live Parallel data. |
| Live verification script | Pass | `python scripts/verify_live.py` — 72 behavioural checks against the deployed service, no credentials needed. |
| Parallel request shapes validated | Pass | `tests/test_parallel_wire_contract.py` asserts the JSON body each of the six surfaces would send, offline. |
| Evaluation harness runs on the real corpus | Pass | `agentic_core/eval/corpus.py`; previously would have failed on the single held-out run. |
| Dependency lock free of prohibited AI tooling | Pass | 111 packages audited; only google-adk, google-genai, google-cloud-aiplatform, parallel-web. |
| Devpost draft and video shot list | Pass | `docs/DEVPOST.md`, `docs/DEMO-VIDEO.md` — owner still records and submits. |
| Design system and principles | Pass | `docs/DESIGN.md`; WCAG AA contrast in both themes, automated a11y audit clean, no horizontal scroll 320–1440px, print stylesheet for filing a dossier. |
| **Parallel runtime** | **PASS — live** | Credential attached 2026-09-07. `/health/integrations` returns a real `search_id`; all six surfaces report live on `/v1/stack`. |
| Ten-fragment evaluation set | Pass | Five development + five sealed holdout clips with hashes and rights record. |
| Control-arm ablation | **Measured** | `docs/ABLATION.md`, `GET /v1/eval/ablation`. 15 runs. Gemini alone: 0 false-confident IDs, but 7/7 identifications unsourceable and 3/3 cases unstable across repeats. |
| Held-out evaluation | Intentionally not run | Run once only after live development cases pass and `eval-freeze-*` is tagged. |
| Public demo video, no more than 3 minutes | Owner action | Record and publish after live Parallel proof. |
| Devpost submission | Owner action | Complete after video and evidence links are final. |
| Standards conformance | **Tested** | `docs/STANDARDS-CONFORMANCE.md`, `GET /v1/standards`. 7 requirements from FIAF (2016) and EN 15907, each page-cited and test-backed. 5 conform, 2 partial, 1 was failing (FIAF A.2.5 devised titles) and is now fixed. |
| Ablation Arm B — control through the real gate | **Measured** | 7 control identifications, 0 survive the gate. Proves the gate is not a rubber stamp. |
| Ablation Arm C — full system | **Measured, one pass** | `GET /v1/eval/arm-c`. Five dev fragments, all six surfaces live: 2 of 3 identifiable cases surfaced correctly against the sealed key, 0 false-confident, 1 miss (D04), 0 language violations. **Do not quote these without the caveat** — see the row below. |
| Verdict stability | **Measured** | `GET /v1/eval/stability`. Repeating that pass showed only 1 of 5 cases giving the same verdict every time, and 9 false-confident identifications across 28 runs where the single pass had none. D04 returned the same wrong film in 3 of 4 runs. `probable` was never reached in any run. Two defects were found and fixed: the candidate slot accepted non-films (`app/works.py`), and hypotheses were never opposed (two Heuer thresholds in the gate). |
| Five development cases run live | **Pass** | D01 abstain ✓, D02 *Dud Leaves Home* (1919) exact, D03 candidates ✓, D04 missed, D05 *Through the Breakers* (1909) exact with the supplied label contradicted. |
| External archivist validation | Outreach action | Still none. Standards conformance is weaker evidence and is not offered as a substitute. Obtain a practitioner review; do not invent endorsement. |

No missing external dependency is represented as passing. `GET /health/integrations`,
`GET /v1/stack` and the ribbon on every page all report Parallel as unavailable until the
credential is attached.
