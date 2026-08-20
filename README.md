# Last Seen Alive

Before an unidentified reel is discarded, investigate whether its clues support a probable
identity—and show exactly where the evidence stops.

> Build status: deployed. Google ADK/Gemini is live; Parallel execution remains fail-closed until
> a real sponsor credential is attached. The held-out result remains intentionally unpublished.

## The 60-second explanation

Film archives receive fragments with missing or unreliable labels. Last Seen Alive transcribes
rare visible clues, searches historical sources, checks worldwide holdings and alternate titles,
then tries to disprove its own candidates. It gives an archivist an evidence dossier, not an
answer from a chatbot. Pure code decides whether each evidence threshold passed, and a probable
identity always requires explicit human approval.

## Live product and public API

- Product: https://last-seen-alive-109051079423.us-central1.run.app
- API docs: https://last-seen-alive-109051079423.us-central1.run.app/docs
- Judge access: the landing page mints a 60-day key without email
- Local: `uvicorn app.api.main:app --reload`

Every identification response exposes `meta.gate.passed`, `meta.gate.failed`, latency, source
coverage and abstention reason. An abstention is HTTP 200 because it is a valid outcome.

## Evaluation

The held-out result is **not run**. Five fragments remain sealed until:

1. the five development cases pass the live Parallel workflow;
2. the implementation is committed and tagged `eval-freeze-*`;
3. the five held-out cases are then run exactly once.

The evaluator records every corpus SHA-256 and refuses a second held-out attempt. The primary
safety metric is false-confident identifications; the target is zero. Failures will remain in the
committed report.

## Architecture

```text
fragment
   │
   ▼
Visual Examiner (Gemini multimodal) ── typed, verbatim clues
   │
   ▼
Phrase Hunter (Parallel Search API) ── cited historical excerpts
   │
   ▼
Holdings Researcher (Parallel Task) ── titles, regions, named catalogues
   │
   ▼
Skeptic (Gemini + Parallel Search) ── cited contradiction attempts
   │
   ▼
IdentityGate (pure Python) ── probable / candidates / abstain
   │
   ▼
archivist approval + evidence dossier
```

All four ADK outputs live under separate state keys and are inspectable. Generated prose is a
view over immutable claims; it is never the source of truth. See [the full architecture](docs/ARCHITECTURE.md).

## Why not just use a screenshot matcher?

Our documented prior-art search found screenshot identifiers, archive cataloguing products and
crowdsourced identification projects, but did not find a production system combining multimodal
clue extraction, live open-web historical investigation, adversarial verification, global
holdings research and claim-level provenance. This is a documented search result, not a claim
that private systems cannot exist. See [prior art](docs/PRIOR-ART.md).

## Google Cloud runtime use

| Service | Runtime call site | Why it is required |
|---|---|---|
| Google ADK | `app/adk_app.py` | Runs the fixed four-role workflow and preserves each output in state. |
| Gemini on Vertex AI | `agentic_core/agents/gemini.py`, `app/adk_app.py` | Reads multimodal clues and performs adversarial interpretation; never owns the verdict. |
| Cloud Run | `Dockerfile`, `infra/deploy.sh` | Hosts the API and product surface. |
| Vertex AI | `app/adk_runtime.py` | Executes Gemini inside the ADK workflow using the Cloud Run service identity. |

## Parallel runtime use

| Service | Runtime call site | Why it is required |
|---|---|---|
| Search API v1 | `app/partners/parallel_research.py::search_archival_evidence` | Supplies every open-web result, URL and excerpt used by Phrase Hunter and Skeptic. |
| Task API v1 | `app/partners/parallel_research.py::deep_holdings_research` | Conducts multi-hop alternate-title and holdings investigation. |

Neither path silently falls back. Without `PARALLEL_API_KEY`, investigation fails closed and the
Live Stack panel reports the integration unavailable.

## Limitations and prohibited uses

- This is triage support, not an attribution authority or replacement for an archivist.
- It cannot establish that a reel is the last or only surviving element.
- Digitised English-language sources have better coverage than many other regions and languages.
- A rare phrase may be reused; a face or costume may be misread.
- Never use a generated candidate to alter a catalogue or preservation decision without human review.

See [all limitations](docs/LIMITATIONS.md).

## Reproduce locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.resolved.txt
pip install pytest==9.1.1
pytest -q
uvicorn app.api.main:app --reload
```

Windows activation: `.venv\Scripts\Activate.ps1`.

The lock is audited for prohibited non-Google AI packages. Secrets belong in Secret Manager;
copy `.env.example` only for local development and never commit `.env`.

## Licence and asset rights

Code is Apache-2.0. Demo assets must be self-created, Creative Commons or public domain and are
tracked in [ASSET_RIGHTS.md](ASSET_RIGHTS.md). No published trailers or third-party-owned film
material may appear in the submission.
