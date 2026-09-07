# Control arm: what Gemini alone does with the same fragments

Run it yourself: `python scripts/run_ablation.py --repeats 3 --temp 0.7`
Raw output: [`eval/reports/ablation-control.json`](../eval/reports/ablation-control.json)

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

## Reproducing

```bash
export GOOGLE_CLOUD_PROJECT=agentic-fleet-2026
export GOOGLE_CLOUD_LOCATION=us-central1
export GOOGLE_GENAI_USE_VERTEXAI=true
python scripts/run_ablation.py --repeats 3 --temp 0.7 --write
```

No Parallel credential required. Development split only — a baseline is not a
licence to open the sealed holdout.
