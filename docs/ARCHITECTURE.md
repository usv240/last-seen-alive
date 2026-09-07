# Architecture

## Consequential decision boundary

Gemini can extract, interpret and explain. Parallel can retrieve and research. Neither can issue
the final identity verdict. `IdentityGate` is a pure function over claims and explicit context;
there is no model or network call inside it.

`probable` requires all seven checks:

1. at least three independent source domains;
2. at least two distinct clue families;
3. temporal compatibility;
4. entity compatibility;
5. zero unresolved, verified contradictions;
6. a verified source on every decisive claim;
7. explicit human approval.

If a candidate crosses the evidence floor without all seven checks, the result is `candidates`.
Below the floor, the result is `abstain`. Every boolean is returned to the client.

## Models research, code verifies

The pipeline splits deliberately at the point where research becomes adjudication.

**Model-driven, in `app/adk_app.py`.** Five ADK agents in a fixed sequence. Four research and
write prose; the fifth restates their findings against a Pydantic schema, because prose cannot be
gated and a schema can. The compiler has no tools on purpose: Gemini cannot combine controlled
generation with function calling, and a summariser should not be able to go looking for new
evidence while it is being asked to summarise the evidence already gathered.

Three Parallel surfaces are exposed to these agents as tools, because deciding *when* to search,
when to research holdings and when to enumerate catalogues is a judgement call:

- **Search** (`search_archival_evidence`) — Phrase Hunter and Skeptic.
- **Task** (`deep_holdings_research`) — Holdings Researcher.
- **FindAll** (`census_named_catalogues`) — Holdings Researcher.

**Code-driven, in `app/adk_runtime.py` and `app/partners/parallel_verify.py`.** Nothing below
this line can be argued with by the model that produced the evidence:

1. **Citation registry.** Every URL a claim cites is checked against what Parallel actually
   returned during this run. A URL never retrieved is discarded before the gate sees it, so a
   fabricated citation can only ever weaken a candidate.
2. **Live citation audit (Parallel Extract).** Each surviving decisive citation is re-opened and
   the quoted text is looked for in the live document. `verified` means the excerpt matched a
   search result; `live_verified` means the page still says it today. A source with
   `live_verified is False` is shown to the archivist and refused by `Claim.is_decisive_eligible`.
3. **Falsification fan-out (Parallel Task Group).** In deep mode, one independent run per
   candidate, each asked only to disprove its own candidate and none of which has seen the
   others. The Skeptic agent, sharing one context window, inherits its own earlier conclusions.
4. **Language gate.** `find_prohibited_language` walks every agent output for survival claims
   catalogue searching cannot support. Violations are returned as flagged sentences with the
   permitted formulation, not published as findings.
5. **IdentityGate.** Pure function. Returns the verdict and every threshold.
6. **Cold-case watch (Parallel Monitor).** When the gate abstains, the archivist may leave a
   standing weekly query on the fragment's rarest transcribed strings.

## Evidence graph

A claim has a stable content-derived ID, stance, producing role, confidence basis and zero or
more sources. A source requires an absolute URL, matching hostname, supporting excerpt, retrieval
time, and two independent verification states. An unsourced claim, an unverified claim, or a
claim whose only source failed the live audit may be displayed but cannot contribute to a gate.

Contradictions are retained. The Skeptic's output is not an editorial note; it becomes an
opposing edge in the same graph and blocks the corresponding candidate while unresolved.

## Runtime boundaries

- **Vertex AI / Gemini** — multimodal clue extraction, research direction, contradiction
  interpretation, and schema-constrained compilation.
- **Parallel Search** — all open-web queries for Phrase Hunter and Skeptic.
- **Parallel Task** — multi-hop alternate-title and holdings research, JSON output schema.
- **Parallel FindAll** — the named-catalogue census that coverage language depends on.
- **Parallel Extract** — live re-verification of every decisive citation.
- **Parallel Task Group** — independent per-candidate falsification.
- **Parallel Monitor** — standing watch on unidentified fragments.
- **Cloud Run** — FastAPI, static product surface, demo media, and report endpoints.
- **Secret Manager** — partner credential and API-key signing pepper.

One investigation is one Parallel `session_id`, carried across every surface it touches, so the
retrieval record is a record of one investigation rather than a pile of unrelated requests.

## API-key model

Keys are stateless: tier, expiry and quota are carried inside the key and protected by an HMAC
over a server-side pepper. Cloud Run runs several instances and can replace one at any time; a
key held in process memory would authenticate on the instance that minted it and 401 everywhere
else. What is given up is per-key revocation, which is an acceptable trade for a 60-day
evaluation credential with a hard expiry — rotating the pepper invalidates every outstanding key
at once.

## Failure behavior

Missing partner credentials, a failed source fetch, or malformed evidence never turn into a
model-memory fallback. The affected threshold remains false and the result degrades to candidates
or abstention. The integration health endpoint reports dependency failure separately from overall
HTTP liveness, and the stack ribbon on every page reflects it.

Verification steps are allowed to fail without taking the investigation down: if Extract or Task
Group is unavailable, the response says so and the affected sources keep their unaudited state.
They are never marked verified by default — the safe direction is always the one that makes the
gate harder to pass.
