# Limitations

- A probable identity is not a catalogue authority record.
- The system cannot establish uniqueness or survival status. It can only list named catalogues
  searched and the date of that search.
- Fragments without legible, discriminating strings may be genuinely unidentifiable.
- Searchable trade-paper coverage is geographically and linguistically uneven.
- Optical transcription can change a rare phrase; all decisive text must remain visually reviewable.
- Stock plot language can create plausible but wrong candidates.
- Performer recognition and date estimates are soft clues unless independently corroborated.
- Parallel results can disappear or change; every decisive excerpt is retained with retrieval time.
- Human approval is mandatory. The system must never directly change a catalogue, funding priority
  or preservation decision.

The held-out benchmark contains fragments with known answers and therefore understates the
difficulty of genuinely unidentified material. Evaluation reports must say this beside every
headline number.

## The verdict is not stable across runs

This is the most important limitation on the page and it was found late, by running
the development split a second time to capture dossiers for the site.

**Across 28 runs of the five development fragments, only one case gave the same
verdict every time.** D02 returned four different leading candidates in four runs —
the correct film once, the studio once, and two other films. D04 returned *Un coin
de Paris (1900)* in three of four runs, at five of seven thresholds, where the key
says *Buying a cow* (1908): a **reproducible** misidentification, which is worse
than a random one. Across all 28 runs there are **nine** false-confident
identifications, or sixteen if every candidate that named no film is counted as one.

The causes are structural, not a bug to be fixed before the deadline: five agents
make live calls against a web that changes between runs, and the model is sampled
rather than replayed.

Consequences a reader should hold onto:

- **A single pass is a sample, not a measurement.** Any figure quoted from one
  pass — including every number in the Arm C column — carries that caveat.
- **"Zero false-confident identifications" is a property of one pass, not of the
  system.** Across all recorded passes it is not zero.
- **Four passes over five fragments is a disclosure, not a rate.** Nineteen runs
  is nowhere near enough to state a false-confident percentage, and none is stated.
- **Reliability is part of this.** Of 20 attempted runs one took 95 minutes and one
  returned HTTP 502. Both are kept in the study, because a caller experiences them.
  The 502 is not a lost investigation so much as a lost answer: Cloud Run logged it
  about 100ms after the application had logged `200 OK` for the same request. Retrying
  costs a second full run and a second set of partner calls.

What did hold across all 28 runs: **`probable` was never reached.** That
threshold requires human approval the API cannot supply, so every result above —
including the wrong one — was returned as `candidates` or `abstain` with its failing
thresholds attached. The defensible claim is not that this system is not wrong. It
is that it does not assert what it cannot support, and shows its working.

Full study, every pass: `/v1/eval/stability`.


## Limits of the verification steps

- The live citation audit confirms a quotation is on the page **today**. It cannot
  tell you the page said the same thing when it was published, and a page that has
  been revised will fail the audit even though the original citation was sound.
  A failed audit lowers confidence; it is not proof the claim is false.
- The audit is capped at eight pages per investigation and the falsification
  fan-out at four candidates. Beyond those ceilings, evidence is compiled but not
  re-verified, and the response says so rather than implying full coverage.
- The named-catalogue census reaches institutions with public, machine-readable
  catalogues. Archives whose holdings are offline, uncatalogued, or described only
  in a printed finding aid are invisible to it. This is exactly why the permitted
  sentence names the catalogues searched and claims nothing about the rest.
- A cold-case monitor watches the strings the Visual Examiner could transcribe. A
  fragment with no legible text yields nothing to watch, and the endpoint declines
  rather than registering a monitor that would only produce noise.

## Limits on material you supply

- An uploaded fragment is read by Gemini on Vertex AI, and text drawn from it is
  sent to Parallel as search queries. That is the investigation; it cannot be done
  locally. Do not upload material you are not free to send to those two services.
- The file is held in memory for the request only and is never written to disk,
  logged, retained, or used for training — but it has still left your premises.
- A supplied catalogue label reaches the model. It is length-capped and quoted
  rather than trusted, and the deterministic gate, the citation registry and the
  live audit all sit downstream of anything the model concludes, so a label cannot
  manufacture a verdict. It can still waste an investigation.
- The system has been evaluated on 50-second excerpts of digitised 35mm material
  from one collection. Behaviour on video-native material, on heavily degraded
  scans, or on single frames is unmeasured.
