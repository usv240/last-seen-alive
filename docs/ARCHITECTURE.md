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

## Evidence graph

A claim has a stable content-derived ID, stance, producing role, confidence basis and zero or
more sources. A source requires an absolute URL, matching hostname, supporting excerpt,
retrieval time and verification state. An unsourced or unverified claim may be displayed but
cannot contribute to a gate.

Contradictions are retained. The Skeptic's output is not an editorial note; it becomes an
opposing edge in the same graph and blocks the corresponding candidate while unresolved.

## Runtime boundaries

- Vertex AI / Gemini: multimodal clue extraction and contradiction interpretation.
- Parallel Search: all open-web queries for Phrase Hunter and Skeptic.
- Parallel Task: multi-hop alternate-title and holdings research.
- Cloud Run: FastAPI, static product surface and job/report endpoints.
- Secret Manager: partner credentials and API-key pepper.
- BigQuery: evidence graphs, evaluations and operational telemetry (provisioning pending).

## Failure behavior

Missing partner credentials, a failed source fetch or malformed evidence never turns into a
model-memory fallback. The affected threshold remains false and the result degrades to candidates
or abstention. The integration health endpoint reports dependency failure separately from overall
HTTP liveness.

