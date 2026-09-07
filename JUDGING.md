# Judge path

Five minutes, no signup, no email.

## Look at these four things

| | |
|---|---|
| 1. **The product** | [`/`](https://last-seen-alive-109051079423.us-central1.run.app) — what the failure is and how the workflow answers it. |
| 2. **The demo set** | [`/presets`](https://last-seen-alive-109051079423.us-central1.run.app/presets) — ten Library of Congress fragments. Watch them, download them, run the five development cases. Note that **five of the ten must not be identified**: two abstentions, two ranked-candidate traps and one case whose supplied catalogue label the record itself contradicts. A system that identifies all ten has failed. |
| 3. **The API** | [`/api`](https://last-seen-alive-109051079423.us-central1.run.app/api) — mint a 60-day key and fire a real request from the page. The site has no privileged internal path; every button on it calls these same public endpoints. |
| 4. **The stack** | [`/stack`](https://last-seen-alive-109051079423.us-central1.run.app/stack) — every Google Cloud and Parallel surface with the module and function that calls it, and its live status. Also available as JSON at `/v1/stack`. |

## Stage-one viability

- Track: **Parallel**.
- Google ADK, Gemini on Vertex AI, Vertex controlled generation, Cloud Run and Secret Manager are
  live.
- All six Parallel surfaces — Search, Task, FindAll, Extract, Task Group, Monitor — are
  implemented against the official `parallel-web` SDK, exercised in tests, and **fail closed**.
- **The mandatory Parallel Search runtime is not yet eligible.** `/health/integrations` reports
  `credential_not_configured` until the sponsor credential is attached in Secret Manager. Nothing
  in this repository or product claims otherwise. See
  [`docs/AUDIT-2026-09-05.md §4`](docs/AUDIT-2026-09-05.md) for exactly how that is cleared.
- Five development and five sealed holdout fragments are hashed and physically separated. Holdout
  routes return HTTP 423 before reading a file, and holdout media is never served.

## Four equal judging criteria

| Criterion | Strongest proof | Remaining proof needed |
|---|---|---|
| Technological Implementation | All six Parallel surfaces used for distinct, necessary jobs; five-role ADK workflow; typed claims; live citation audit via Extract; independent falsification via Task Group; deterministic gate; sealed evaluation controls | Live Search, Task, FindAll, Extract and Task Group responses from a real Parallel account |
| Design | Four coherent pages, watchable and downloadable demo set, bring-your-own upload, a working API playground, live sponsor stack on every page, explicit abstention as a first-class outcome | Re-run the complete visible workflow after Parallel activation |
| Potential Impact | Evidence-first archive triage, zero false-confident-ID target, a cold-case watch so an abstention is not a dead end | Independent archivist review and an honest frozen holdout result |
| Quality of Idea | Multimodal clue extraction plus adversarial historical research, not screenshot similarity; verification separated from research in code, not in a prompt | Preserve prior-art scope and report multilingual coverage gaps |

## What to check if you want to be adversarial

- `POST /v1/identify` with `{"sample_id":"H01"}` → **423**. The holdout is sealed even with a
  valid key.
- `GET /v1/presets/H01/media` → **423**. Holdout media is never served on any path.
- Compare the SHA-256 in `X-Fragment-SHA256` on any development media response against
  `/v1/eval/manifest`. They match; the hash is not decoration.
- Remove the Parallel credential and every surface raises rather than answering from model
  memory. `tests/test_parallel_surfaces.py::test_every_surface_fails_closed_without_a_credential`
  asserts this for all six.
- Look for the discriminating evidence in `/v1/presets`. It is not there — the site's own copy is
  written to avoid quoting the clue the workflow is meant to find, while `/v1/eval/manifest`
  publishes it in full. `test_preset_listing_does_not_leak_the_discriminating_evidence` enforces it.

## Required activation order

1. Attach `last-seen-alive-parallel-api-key` from Secret Manager; never expose it to the UI or
   repository. `infra/deploy.sh` detects and binds it.
2. Make five development cases pass through the live surfaces.
3. Commit and sign `eval-freeze-*`.
4. Run the five holdouts exactly once and commit all misses.
5. Only then record the public demo.

An abstention is a correct product outcome and returns HTTP 200. The system is triage support,
not an archival attribution authority.
