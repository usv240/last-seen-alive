# Ablation: what the research and the gate are actually worth

Run the control: `python scripts/run_ablation.py --repeats 3 --temp 0.7`
Raw output: [`ablation-control.json`](../eval/reports/ablation-control.json) (Arms A and B) · [`arm-c-development.json`](../eval/reports/arm-c-development.json) (Arm C)

This project claims that live open-web research plus deterministic gating
produces something an archivist can act on, where a capable multimodal model
alone does not. That claim is worthless unless someone measures the alternative,
so this is the measurement.

The control gives Gemini 2.5 Flash the **identical fragment**, with no tools, no
web access, no citation registry and no gate. Same model, same media, and a
prompt that asks the question a working archivist would ask. It is not a straw
man, and it needs only Vertex AI — which is why it could be run before the
Parallel credential existed, rather than afterwards when the number would have
been easier to rationalise.

**15 runs, 5 development fragments, 3 samples each, temperature 0.7,
`gemini-2.5-flash`, 2026-09-07.** The held-out split was not touched.

---

## The result that contradicted our own assumption

This was built expecting an ungated model to name a film for everything. **It did
not.** On the six runs covering the two fragments whose visible evidence cannot
support an identification, Gemini named a film **zero times**.

| | Control arm |
|---|---:|
| Runs where no identification is possible | 6 |
| **False-confident identifications** | **0** |

D01 — a dark interior with nothing legible — was declined 3/3, with the model
correctly noting the absence of identifying features. D03, the ambiguity trap,
was declined 3/3 on the grounds that the staging was generic.

That number is reported first, and unchanged. A benchmark you rewrite after
seeing its answer measures nothing. **Gemini is well calibrated about *whether*
to answer**, and any pitch claiming otherwise would be false.

## The result that matters instead

Asked the same question three times, the model gave different answers — every
one at **high** confidence.

| Case | Required behaviour | Distinct answers in 3 runs | Confidence |
|---|---|---:|---|
| D01 | abstain | 1 (declined every time) | none |
| D03 | candidates | 1 (declined every time) | none |
| **D02** | identify | **3** | high, high, high |
| **D04** | identify | **3** | high, high, high |
| **D05** | contradict | **2** | high, none, none |

- **D02** returned *Bobby Bumps' Midnight Auto Ride* (1917), then *Bobby Bumps'
  Night Out* (1917), then *Bobby Bumps' Night Out* (**1918**). Three answers, two
  years, all "high".
- **D04** returned *La Vache qui prend le Métro* dated 1905, then 1905, then
  **1908** — and a separate greedy run at temperature 0 returned a different
  title again, *La Vache qui veut entrer au Métro*.
- **D05** returned *The Way of the World* (1910) once and declined twice; the
  greedy run returned *The Nervous Wreck* (1913). Three different behaviours
  across four samples of one fragment.

**Every identification it made — 7 of 7 — carried no citable source.**

| | Control arm |
|---|---:|
| Identifications made | 7 |
| ...with no citable source | 7 (rate **1.0**) |
| Cases unstable across repeats | D02, D04, D05 |
| Runs that ignored a supplied catalogue title | 1 of 3 |
| Median latency | 14.7 s |

Be fair about the sourcing figure: the control has no web access, so it *cannot*
cite by construction. That is not a gotcha, it is the point — this is what you
get if you do not build the research layer. The instability is different. That is
not an artifact of the setup, and it is not fixed by giving the model a better
prompt.

## Arm B — the same answers, through the real gate

Arm A measures a capable model alone. Arm C, the full system, needs the Parallel
credential and cannot run yet. Arm B sits between them and needs nothing new:
take exactly what the control said and pass it through the **production**
`build_evidence` and the **production** `IdentityGate`, with an empty citation
registry — the honest representation of a run in which nothing was retrieved.

This is not circular. It answers a question neither other arm does: **is the gate
doing work, or is it a rubber stamp?**

| | Arm A: control | Arm B: control + gate |
|---|---:|---:|
| Identifications presented as such | **7** | **0** |
| Verdicts produced | 7 × "high confidence" | `abstain`, `candidates` |
| Thresholds failed | n/a | `independent_source_domains>=3`, `distinct_clue_families>=2`, `every_decisive_claim_has_source`, `human_approved` |

Every high-confidence identification the control made was refused, on the
threshold that no source supported it. The gate is not decoration.

Note *how* it refuses. The answers become `candidates`, not `abstain` — the
model's guess is not hidden, it is **labelled as unsupported** and shown with the
exact thresholds it failed. An archivist still sees "Bobby Bumps' Night Out" as
something to look into; what they no longer see is a confident assertion they
cannot check. That is the difference between suppressing a model and grounding
one.

### What Arm B cannot show

It establishes that unsourced claims cannot pass. It says nothing about the other
direction: whether real open-web evidence lifts a fragment **above** the
threshold, or whether the system merely fails more expensively than the control
does. A gate that refuses everything is trivially safe and useless.

That is exactly the question the Parallel credential unblocks, and it is why this
is a two-arm result rather than a three-arm one. When the credential lands, the
same five fragments run as Arm C and the third column is published — **including
if it shows the full system never gets past its own gate.**

## Arm C — the full system, measured 2026-09-07

> **Read the stability section below before quoting any number in this table.**
> This arm is a *single pass*. Later passes over the same five fragments disagreed
> with it on four of five verdicts and reproduced neither correct identity. The
> table stands as the record of what that pass did; it is not this system's result.

The Parallel credential arrived, so the third arm exists. Same five fragments,
`standard` depth, `gemini-2.5-flash`, all six Parallel surfaces live.

| | A: Gemini alone | B: A + the gate | **C: full system** |
|---|---:|---:|---:|
| Correct identities surfaced | **0** of 3 | 0 of 3 | **2** of 3 |
| False-confident identifications | 0 | 0 | **0** |
| Identifications with no citable source | 7 of 7 | — | **0** |
| Answers unstable across repeats | 3 of 3 cases | — | **4 of 5 verdicts moved** (see below) |
| Median latency | 15 s | 15 s | **383 s** |

Per case, against the sealed answer key:

| Case | Required | Verdict | Answer key | System's leading candidate | |
|---|---|---|---|---|---|
| D01 | abstain | `abstain` | *Ghosts* | — none — | correct |
| D02 | identify | `candidates` | *Dud leaves home* (1919) | **Dud Leaves Home (1919)** | **exact** |
| D03 | candidates | `candidates` | *The rival brothers' patriotism* | *Early to Mid-20th Century Civilian and Workwear* | no film named |
| D04 | identify | `abstain` | *Buying a cow* | — none — | **missed** |
| D05 | contradict | `candidates` | *Through the breakers* (1909) | **Through the Breakers (1909)** | **exact** |

### What changed between the arms

**D02.** The control returned *Bobby Bumps' Night Out* (1917), then *Bobby Bumps'
Midnight Auto Ride*, then *Bobby Bumps' Night Out* (1918) — three answers, all
"high" confidence, none sourced, all wrong. The full system returned **Dud Leaves
Home (1919)**, which is the answer key exactly, supported by 9 decisive claims
across 9 independent domains, and it cited `loc.gov/item/00694010` — the very LOC
record the benchmark was built from. Six of six cited pages were re-opened by
Parallel Extract and confirmed.

**D05, the misattribution case.** The fragment arrives labelled *"Those who pay"*.
The control replaced that with *The Nervous Wreck* (1913) on one run and *The Way
of the World* (1910) on another, and on one run never mentioned the supplied
title at all. The full system surfaced **Through the Breakers (1909)** — the
documented correction — with a contradiction claim citing the Library of Congress
record. That is the FIAF rule "correct it only when it is known to be ambiguous
or erroneous" behaving as intended.

**Neither result was reachable without the open web.** These are 1909 and 1919
titles whose evidence lives in trade papers and catalogue records, not in model
weights.

### The stability problem, found afterwards

Capturing dossiers for the site meant running these five fragments a second time.
The second pass disagreed with the table above on **four of five verdicts**:

| Case | Arm C pass | Second pass | Answer key |
|---|---|---|---|
| D01 | `abstain` | `candidates` — *An unidentified film fragment* | *Ghosts* (1915) |
| D02 | `candidates` — **Dud Leaves Home (1919)** ✓ | `candidates` — *Bray Studios Inc.* | *Dud leaves home* (1919) |
| D03 | `candidates` — *costume cluster* | `abstain` | *The rival brothers' patriotism* (1911) |
| D04 | `abstain` | `candidates` — *Un coin de Paris (1900)* | *Buying a cow* (1908) |
| D05 | `candidates` — **Through the Breakers (1909)** ✓ | `abstain` — *Those who pay* | *Through the breakers* (1909) |

Two things follow, and neither is comfortable.

**Neither correct identity reproduced.** The two results this ablation leads with
were not repeatable on the next run. On D02 the leading candidate came back as the
studio rather than the film.

**"Zero false-confident identifications" does not survive.** By the definition
published with this report — *the system put forward a specific film as the leading
candidate and the answer key says it is the wrong film* — the second pass has
**one**: D04 returned *Un coin de Paris (1900)*, alone, at five of seven thresholds,
where the key says *Buying a cow*. That is scored as a false-confident
identification in `eval/reports/stability.json` rather than argued away.

**What did hold.** No run, in any pass, reached `probable`. Every one of these
results was returned as `candidates` or `abstain`, with the failing thresholds
attached — including the wrong one, where `unresolved_contradictions==0` failed
because the Skeptic had found the contradiction. The defensible claim is not "this
system is not wrong". It is "this system does not assert what it cannot support,
and shows you why" — which is weaker, and true.

The full study, every pass including the bad ones, is at `/v1/eval/stability`
(`scripts/run_stability.py`, scored by `scripts/score_stability.py`).

### The miss, and why it is the right kind

**D04 abstained where the answer key says *Buying a cow*.** The research worked:
13 independent domains, the Visual Examiner correctly transcribed "LOUVRE" and
"TABAC" from a horse-drawn omnibus. Then **ten citations were rejected** — eight
because the compiler paraphrased rather than quoting what Parallel returned
verbatim, two because Parallel Extract could not find the quoted text on the live
page. Zero decisive claims survived, so the gate abstained.

That is the citation registry doing exactly what it was built to do, and it cost
us a recall point. **The strictness that produces zero false-confident
identifications is the same strictness that produced this miss.** We are not
going to loosen it to improve the number; a system that accepts paraphrased
citations has given up the only thing it was offering.

### A defect the run exposed

D03 returned a candidate called `early_to_mid_20th_century_costume`, labelled
*"Early to Mid-20th Century Civilian and Workwear"*. That is a costume-period
cluster, not a film. The required behaviour — ranked candidates, no verdict — was
met, and no film was misidentified. But a candidate slot is for a candidate
**work**, and the compiler filled it with an observation. Scored here as a
malformed candidate rather than a false-confident identification; the label is
published so that judgement can be disputed.

### Honest reading of "2 of 5"

Only two cases matched their required outcome exactly, and that number needs the
asterisk it comes with: **`identify` is unreachable through the API by design.**
`human_approved` is a gate threshold only an archivist can satisfy, so `probable`
is never returned to a caller. D02 surfaced the correct identity with five of
seven thresholds passed, failing only an unresolved contradiction and human
approval. Calling that a failure against `identify` would be scoring the system
against something it deliberately refuses to do.

The metric that carries the product's claim is the second row of the table, and
it is **0** in every arm — including the control, which was well calibrated about
when to decline. What the full system adds is not restraint. It is *sourced,
correct answers where the control produced unsourced, unstable, wrong ones*.

## Why this is the argument

A cataloguer runs this once. They get one of three titles, possibly with the
wrong year, presented at high confidence with no way to check it. They cannot
tell which run they got, and neither can the next person to read the record.
That is precisely how a plausible misattribution enters a catalogue and stays
there for thirty years.

The full system responds to each of those failures with a mechanism rather than
an instruction:

| Control failure | Mechanism in the full system |
|---|---|
| No source for any identification | Citation registry discards any URL Parallel did not return in that run |
| A source that cannot be re-checked | Parallel Extract re-opens each cited page; a quotation absent from the live document is refused by the gate |
| Different answer each run, all "high" | The verdict is a pure function of counted, sourced claims — not of the model's confidence, which the gate never reads |
| A supplied catalogue title silently replaced | The Skeptic and the Tier E case require the conflict to be surfaced, not inherited |

Note what the gate never consumes: the model's own confidence. Nothing in
`IdentityGate` reads it. A high-confidence unsourced claim contributes exactly
nothing.

## What this does not show

- **n = 3 per case**, one model, one temperature, five fragments, one collection.
  Enough to demonstrate instability, not enough to put a rate on it.
- **The full system has not been measured on these cases**, because the Parallel
  credential does not exist yet. This is a baseline with no comparison line. When
  the credential lands, the same five fragments run through the full pipeline and
  both columns get published — including if the full system does worse.
- **Correctness is not scored here.** Whether *Bobby Bumps' Night Out* is right
  is not the question; that answers are mutually inconsistent, unsourced and
  confident is the question.
- The control is **faster** — 14.7 s against 40–120 s for the full pipeline. That
  is a real cost, honestly stated.
- **Neither arm has been reviewed by an archivist.** Conformance to the published
  cataloguing standards is tested separately in
  [STANDARDS-CONFORMANCE.md](STANDARDS-CONFORMANCE.md); that is weaker evidence than a
  practitioner review and is not offered as a replacement for one.

## Reproducing

```bash
export GOOGLE_CLOUD_PROJECT=agentic-fleet-2026
export GOOGLE_CLOUD_LOCATION=us-central1
export GOOGLE_GENAI_USE_VERTEXAI=true
python scripts/run_ablation.py --repeats 3 --temp 0.7 --write
```

No Parallel credential required. Development split only — a baseline is not a
licence to open the sealed holdout.
