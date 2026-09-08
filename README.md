# Last Seen Alive

Before an unidentified reel is discarded, investigate whether its clues support a probable
identity—and show exactly where the evidence stops.

> Build status: deployed and fully live. Google ADK/Gemini and all six Parallel surfaces are
> running against real credentials. The five development fragments have been investigated
> end to end; the held-out result remains intentionally unpublished.

## The 60-second explanation

Film archives receive fragments with missing or unreliable labels. Last Seen Alive transcribes
rare visible clues, searches historical sources, checks worldwide holdings and alternate titles,
re-opens every page it cites to confirm the quotation is really there, and tries to disprove its
own candidates. It gives an archivist an evidence dossier, not an answer from a chatbot. Pure
code decides whether each evidence threshold passed, and a probable identity always requires
explicit human approval.

## Live product and public API

| | |
|---|---|
| Product | https://last-seen-alive-109051079423.us-central1.run.app |
| Demo fragments | [`/presets`](https://last-seen-alive-109051079423.us-central1.run.app/presets) — watch, download, and run all ten |
| API | [`/api`](https://last-seen-alive-109051079423.us-central1.run.app/api) — mint a key and run a live call in the browser |
| Dossiers | [`/dossiers`](https://last-seen-alive-109051079423.us-central1.run.app/dossiers) — complete output from real runs, read it without waiting |
| Practice | [`/practice`](https://last-seen-alive-109051079423.us-central1.run.app/practice) — published practitioner objections, answered or admitted |
| Stability | [`/v1/eval/stability`](https://last-seen-alive-109051079423.us-central1.run.app/v1/eval/stability) — 19 runs of the same five fragments, including the bad ones |
| Stack | [`/stack`](https://last-seen-alive-109051079423.us-central1.run.app/stack) — every sponsor surface with its call site and live status |
| OpenAPI | [`/docs`](https://last-seen-alive-109051079423.us-central1.run.app/docs) |
| Local | `uvicorn app.api.main:app --reload` |

Judge access: `POST /v1/keys` with `{"tier":"judge"}` returns a 60-day key. No email, no signup.
Start with [`JUDGING.md`](JUDGING.md) and the machine-readable
[`submission-evidence.json`](submission-evidence.json).

Every identification response exposes `meta.gate.passed`, `meta.gate.failed`, latency, source
coverage and abstention reason. **An abstention is HTTP 200 because it is a valid outcome.**

## Three ways to use it

1. **Ten public demo fragments.** Library of Congress material, US public domain, watchable and
   downloadable at `/presets`. Five are runnable; five are sealed holdouts listed with their
   hashes so the set cannot be quietly changed. The media endpoint refuses to serve a holdout.
2. **Your own material.** `POST /v1/investigate` takes a short excerpt (48 MB, mp4/mov/webm/
   mkv/jpeg/png/webp) and returns the same dossier. The file is held in memory for the request
   and never written to disk or logged. Frames do travel to Gemini on Vertex AI, and text read
   off them travels to Parallel as search queries — that is the investigation.
3. **As an API in your own catalogue tooling.** Signed stateless keys, a stable error contract,
   and a runnable playground at `/api` that fires real requests from the browser.

## Architecture

```text
fragment
   │
   ▼
Visual Examiner (Gemini multimodal) ──── typed, verbatim clues
   │
   ▼
Phrase Hunter (Parallel Search) ──────── cited historical excerpts
   │
   ▼
Holdings Researcher (Parallel Task + FindAll) ── titles, regions, named catalogues
   │
   ▼
Skeptic (Gemini + Parallel Search) ───── cited contradiction attempts
   │
   ▼
Evidence Compiler (Gemini, schema-constrained) ── typed claims
   │
   ▼ ─── code from here down; no model can change any of it ───
Citation registry ───── discard every URL Parallel did not return this run
Citation audit (Parallel Extract) ── re-open each cited page, check the quotation
Falsification fan-out (Parallel Task Group) ── one independent attacker per candidate
Language gate ───────── refuse survival claims catalogue searching cannot support
IdentityGate ────────── probable / candidates / abstain
   │
   ▼
archivist approval + evidence dossier
   │
   └─ if abstained: Parallel Monitor leaves a standing watch on the fragment's rarest strings
```

Generated prose is a view over immutable claims; it is never the source of truth.
See [the full architecture](docs/ARCHITECTURE.md).

## Google Cloud runtime use

| Service | Runtime call site | Why it is required |
|---|---|---|
| Google ADK | `app/adk_app.py` | Runs the fixed five-role workflow and preserves each output in state. |
| Gemini on Vertex AI | `app/adk_runtime.py`, `app/adk_app.py` | Reads multimodal clues and performs adversarial interpretation; never owns the verdict. |
| Vertex controlled generation | `app/evidence_schema.py` | Forces a typed claim structure. Prose cannot be gated; a schema can. |
| Cloud Run | `Dockerfile`, `infra/deploy.sh` | Hosts the API, product surface and demo media. |
| Secret Manager | `infra/deploy.sh` | Holds the Parallel credential and the API-key signing pepper. |

## Parallel runtime use — all six surfaces

Three are agent tools, because *when* to research is a judgement call. Three are called by
deterministic code, because each exists to check or outlast the model's own work.

| Surface | Call site | What it does here |
|---|---|---|
| **Search API** | `parallel_research.py::search_archival_evidence` | Every open-web fact. Rare intertitles searched as literal quoted strings with long excerpts. Content-recycling domains are excluded at the source-policy level so "three independent domains" cannot be three mirrors of one plot summary. |
| **Task API** | `parallel_research.py::deep_holdings_research` | Multi-hop holdings and alternate-title research against a JSON output schema, with a source policy pointing it at library, archive, `.gov` and `.edu` domains. |
| **FindAll API** | `parallel_research.py::census_named_catalogues` | Enumerates the archives and catalogues whose own records list a candidate. This product may never write "last surviving copy"; the only permitted sentence names the catalogues searched, and FindAll produces that list. |
| **Extract API** | `parallel_verify.py::audit_citations_with_extract` | Re-opens every page a decisive claim cites and looks for the quoted text in the live document. A citation that fails is shown to the archivist and refused by the gate. |
| **Task Group API** | `parallel_verify.py::falsify_candidates_with_task_group` | One independent falsification run per candidate. The Skeptic agent inherits its own earlier conclusions inside one context window; these runs cannot. |
| **Monitor API** | `parallel_verify.py::open_cold_case_monitor` | An abstention is right today and wrong forever — archives digitise continuously. Leaves a standing weekly query on the fragment's rarest transcribed strings. |

Nothing silently falls back. Without `PARALLEL_API_KEY`, every surface raises
`ParallelNotConfigured`, the investigation stops, and the stack ribbon on every page reports the
integration unavailable. `tests/test_parallel_surfaces.py` proves this for all six.

## Read this before quoting any evaluation number

**The published Arm C figures are a single pass and they do not hold.** Running the
same five development fragments four times — **19 runs** — gives a different and
worse picture:

| Across 19 runs | |
|---|---:|
| Cases giving the same verdict every time | **1 of 5** |
| Correct identities | 2 |
| **False-confident identifications** | **5** (12 on the strictest reading) |
| Candidates that named no film at all | 7 |
| **Runs that reached `probable`** | **0** |

D02 returned four different leading candidates in four runs. D04 returned the same
wrong film, *Un coin de Paris* (1900), in three of four runs at five of seven
thresholds — a reproducible misidentification, not noise. Full study, every run
including the 95-minute one and the 502: [`/v1/eval/stability`](https://last-seen-alive-109051079423.us-central1.run.app/v1/eval/stability).

What did hold: **no run ever reached `probable`**, because that threshold requires
human approval the API cannot supply. Every wrong answer arrived as `candidates`
with its failing thresholds attached. The claim this project defends is not that it
is never wrong — it is that it never asserts what it cannot support, and shows its
working.

## The case for it, and the review it has not had

`docs/IMPACT.md` makes the argument from cited sources rather than assertion. The short
version: the Library of Congress census found that **14%** of American silent feature films
survive in their original format, and the Library's own annual identification workshop
identifies **23–30%** of the films it screens each year. Identification is expert-scarce,
happens four days a year in Virginia, and does not scale. This runs continuously, through an
API, and produces a dossier an archivist can audit rather than an answer they must trust.

That comparison is context, not a scoreboard: the corpora are not comparable and five cases
support no rate at all. No claim to outperform expert archivists is made anywhere in this
project.

**No archivist has reviewed this system.** Rather than leave that as a caveat, `/v1/practice`
publishes fourteen demands taken verbatim from published sources — a peer-reviewed evaluation in
which archive experts assessed AI-generated cataloguing ([ArchiveGPT, Abele et al.,
arXiv:2507.07551](https://arxiv.org/abs/2507.07551)), the FIAF manual, and the Library of
Congress's own account of its method — each paired with the mechanism here that answers it.
**Two are marked `not_met`, including the missing review itself.** Every structural claim in
the register is asserted by `tests/test_practitioner_objections.py`, and the two load-bearing
behavioural claims are executed against the real gate rather than described.

## Why not just use a screenshot matcher?

Our documented prior-art search found screenshot identifiers, archive cataloguing products and
crowdsourced identification projects, but did not find a production system combining multimodal
clue extraction, live open-web historical investigation, adversarial verification, global
holdings research and claim-level provenance. This is a documented search result, not a claim
that private systems cannot exist. See [prior art](docs/PRIOR-ART.md).

## Evaluation

### The baseline, measured

Before measuring this system, we measured the alternative: the same five
fragments given to Gemini with no web access, no citation checking and no gate,
three samples each. It needs no partner credential, so it ran first rather than
afterwards when the number would have been easier to rationalise.

It contradicted the assumption it was built to test. Gemini is **well calibrated
about whether to answer** — it declined to name a film on both fragments whose
evidence cannot support one, so false-confident identifications were **zero**.

What it could not do was answer the same question twice. Three runs of one
fragment returned three different titles and two different years, every one at
"high" confidence, and **all 7 identifications it made cited nothing**. A
cataloguer runs it once, gets one of three answers, and cannot tell which.

Full method and caveats: [docs/ABLATION.md](docs/ABLATION.md). Raw result:
[`eval/reports/ablation-control.json`](eval/reports/ablation-control.json) or
`GET /v1/eval/ablation`. Reproduce: `python scripts/run_ablation.py --repeats 3 --temp 0.7`.

### The held-out split

The held-out result is **not run**. Five fragments remain sealed until:

1. the five development cases pass the live Parallel workflow;
2. the implementation is committed and tagged `eval-freeze-*`;
3. the five held-out cases are then run exactly once.

The evaluator records every corpus SHA-256 and refuses a second held-out attempt. The primary
safety metric is false-confident identifications; the target is zero. Failures will remain in the
committed report.

## Limitations and prohibited uses

- This is triage support, not an attribution authority or replacement for an archivist.
- It cannot establish that a reel is the last or only surviving element. Searching every
  catalogue you can name tells you where a print is; it can never tell you no other print exists.
- Digitised English-language sources have better coverage than many other regions and languages.
- A rare phrase may be reused; a face or costume may be misread.
- Never use a generated candidate to alter a catalogue or preservation decision without human
  review.

See [all limitations](docs/LIMITATIONS.md).

## Reproduce locally

```bash
python -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.resolved.txt
pip install pytest==9.1.1 pytest-asyncio==1.3.0 ruff==0.15.6
ruff check .
pytest -q
uvicorn app.api.main:app --reload
```

The full suite runs without network access or credentials: the partner surfaces are exercised
against fakes, and the fail-closed behaviour is asserted with the credential removed.

The lock is audited for prohibited non-Google AI packages. Secrets belong in Secret Manager;
copy `.env.example` only for local development and never commit `.env`.

## Licence and asset rights

Code is Apache-2.0. Demo assets are Library of Congress National Screening Room material,
published by 1929 and in the United States public domain, tracked in
[ASSET_RIGHTS.md](ASSET_RIGHTS.md) and [eval/ASSET_RIGHTS.md](eval/ASSET_RIGHTS.md). Required
credit — *Library of Congress, Motion Picture, Broadcasting, and Recorded Sound Division* —
appears on every media response, every preset card and every page footer. No published trailers
or third-party-owned film material appears in the submission.
