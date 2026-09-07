# Devpost submission draft — Last Seen Alive

Track: **Parallel**. Paste into the Devpost form. Everything marked ⚠️ must be
true at the moment you submit; delete any line you cannot stand behind.

---

## Elevator pitch (200 characters)

> Evidence-first triage for unidentified film fragments: it investigates what a
> nameless reel might be, tries to prove itself wrong, and shows an archivist
> exactly where the evidence stops.

---

## Inspiration

Film archives hold material nobody can name. A can with no label, a reel spliced
from three others, a donation whose paperwork was lost decades ago. Identifying
one is slow, skilled, mostly-fruitless work: read whatever is visible in the
frame, search a century of trade papers for a phrase, check whether some other
archive already knows what it is.

Almost every AI answer to this is a screenshot matcher, which works only when the
answer is already in a reference set — precisely the case that does not apply to
unidentified material. And the failure mode of a confident system here is not a
wrong answer, it is a *plausible* one: a catalogue entry that looks researched,
propagates for thirty years, and quietly misattributes a film.

So the question we built for was not "can a model identify this film" but "can a
system show its evidence honestly enough that an archivist can act on it."

## What it does

Send a fragment — one of ten public-domain Library of Congress demo clips, or
your own file. You get back a dossier, not an answer:

- every claim, with the source behind it and the exact quoted excerpt;
- the contradictions found *against* the leading candidate;
- which citations failed a live re-check, and were therefore refused;
- a seven-threshold deterministic gate, showing every threshold that passed and
  every one that did not;
- a verdict of `probable`, `candidates` or `abstain` — and never `confirmed`,
  because human approval is a gate threshold no API call can satisfy.

An abstention returns HTTP 200. It is a correct outcome, not a failure, and two
of our ten benchmark cases require it.

## How we built it

Five Google ADK agents research; **deterministic code verifies**; a human decides.

Gemini on Vertex AI reads the fragment and transcribes visible text verbatim.
Parallel Search hunts the rarest strings as literal quoted phrases. Parallel Task
researches holdings against a JSON output schema. Parallel FindAll enumerates the
archives whose own catalogues list a candidate. A Skeptic agent searches for
evidence against every candidate. A schema-constrained compiler turns the prose
into typed claims — because prose cannot be gated, and a schema can.

Then code takes over, and nothing below this line can be argued with by the model
that produced the evidence:

1. Every citation is checked against what Parallel actually returned in that run.
   A URL never retrieved is discarded before the gate sees it.
2. **Parallel Extract re-opens every surviving decisive citation** and looks for
   the quotation in the live document. This is the difference between "a search
   snippet contained this" and "the page still says this". A citation that fails
   is shown to the archivist and refused by the gate.
3. **Parallel Task Group** fans out one independent falsification run per
   candidate, each asked only to disprove its own and none of which has seen the
   others.
4. Every generated sentence is scanned for survival claims that catalogue
   searching cannot support.
5. A pure function reads the thresholds and returns the verdict.
6. If the gate abstains, **Parallel Monitor** leaves a standing weekly query on
   the strings visible in the frame — because archives digitise continuously, and
   an abstention is the right answer today and the wrong answer forever.

All six of Parallel's product surfaces, five Google Cloud services, and every one
of them doing a job the product needs. `/stack` shows each with the exact module
and function that calls it, and whether it is reachable right now.

## Challenges we ran into

**"It never says last surviving copy" was a prompt instruction, which is not a
control.** Searching every catalogue you can name tells you where a print is; it
can never tell you no other print exists. We made it real twice over: a language
gate that scans every agent output and surfaces violations as flagged sentences
rather than findings, and FindAll producing the *named list* that the only
permitted sentence depends on.

**A model asked to preserve citations will sometimes produce one that looks
correct and was never retrieved.** Instructions cannot prevent that; only checking
can. Hence the citation registry, and then the live Extract audit on top of it. A
fabricated citation can now only ever *weaken* a verdict.

**Our own API did not work.** Keys were held in process memory, and Cloud Run runs
several instances — so a key minted on the landing page would have failed on
roughly three calls in four. They are now HMAC-signed and stateless, verifying on
any instance.

**A 48 MB upload was an out-of-memory button.** Cloud Run's filesystem is
memory-backed and Starlette spools multipart bodies to it, so at the platform
default of 80 concurrent requests the maths came to ~4 GB against a 1 GB limit.

## Accomplishments we're proud of

The benchmark is built to be failed. Ten fragments, and **five of them must not be
identified**: two abstentions, two ambiguity traps that permit only ranked
candidates, and one that arrives carrying a catalogue label the Library of
Congress record itself contradicts. A system that identifies all ten has failed.
Five are sealed, published with their SHA-256 hashes, and the media endpoint
refuses to serve them.

`python scripts/verify_live.py` runs 72 checks against the deployed service and
verifies the claims this page makes — including that the bytes served for a demo
fragment hash to the value the manifest publishes.

## What we learned

Separating research from adjudication in *code* rather than in a prompt changed
what the system could honestly claim. Once the gate could not be talked to, every
other decision got easier: uncertainty became a designed output instead of a
failure state, and "we could not identify this" became a feature with an action
attached to it rather than an apology.

## What's next

An archivist review — the one thing we could not manufacture and the thing this
most needs. Then the sealed holdout, run exactly once, with every miss published
next to the successes.

---

## Form fields

| Field | Value |
|---|---|
| Track | Parallel |
| Hosted project URL | https://last-seen-alive-109051079423.us-central1.run.app |
| Repository | https://github.com/usv240/last-seen-alive |
| Licence | Apache-2.0 (detected in the repository About section) |
| Video | ⚠️ paste the YouTube/Vimeo URL, public, ≤ 3 minutes |
| Google Cloud products | Agent Development Kit, Gemini on Vertex AI, Vertex AI controlled generation, Cloud Run, Secret Manager |
| Partner products | Parallel Search API, Task API, FindAll API, Extract API, Task Group API, Monitor API |
| Other data sources | Library of Congress National Screening Room (US public domain, published by 1929) |

**Judge access:** no signup and no email. `POST /v1/keys` with `{"tier":"judge"}`
returns a 60-day key, or press the button on the landing page.

---

## ⚠️ Do not submit until these are true

- [ ] `GET /health/integrations` reports `parallel_search.ok = true` on the live
      service. Until then the Parallel track requirement is **not met**, and
      Stage One is a fail regardless of anything else on this page.
- [ ] All five development fragments have been through the live workflow.
- [ ] The demo video shows the real product, is under 3 minutes, is public, and
      displays no third-party logo or trademark.
- [ ] Every claim above is still true. Delete anything that is not.
