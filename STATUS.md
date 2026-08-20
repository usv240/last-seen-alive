# Submission status

Last verified: 2026-08-20.

| Gate | Status | Evidence / next action |
|---|---|---|
| Public standalone repository + Apache-2.0 | Pass | GitHub repository and detected licence. |
| Hosted product | Pass | Cloud Run revision `last-seen-alive-00006-zgb`; public API and no-signup judge key. |
| Google ADK + Gemini runtime | Pass | `app/adk_runtime.py`; live Vertex health probe. |
| Parallel runtime | Blocked externally | Code uses Search v1 and Task v1 and fails closed; attach sponsor credential in Secret Manager. |
| Ten-fragment evaluation set | Pass | Five development + five sealed holdout clips with hashes and rights record. |
| Held-out evaluation | Intentionally not run | Run once only after live development cases pass and `eval-freeze-*` is tagged. |
| Public demo video, no more than 3 minutes | Owner action | Record and publish after live Parallel proof. |
| Devpost submission | Owner action | Complete after video and evidence links are final. |
| External archivist validation | Outreach action | Obtain review of workflow, claims, and limitations; do not invent endorsement. |

No missing external dependency is represented as passing.

Machine-readable live checks are recorded in `docs/LIVE-ACCEPTANCE.json` with no credentials.
