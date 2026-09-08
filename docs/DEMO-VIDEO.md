# Demo video — shot list and script

Hard limit **3 minutes**; only the first three are evaluated. Public on YouTube
or Vimeo. English, or English subtitles.

**Record it only after `/health/integrations` reports Parallel live.** A video of
the fail-closed state would show the product refusing to work, which is honest
but is not what three minutes should be spent on.

## The constraint that shapes this edit

An investigation takes **225–430 seconds**, median 383 — measured, published at
`/v1/eval/arm-c`, and stated on screen by the product itself. **You cannot show a
complete live run inside a three-minute video.** An earlier version of this script
said "let the run console play, do not cut away from it". That is no longer
possible and pretending otherwise would mean either faking a fast run or spending
the entire video on a progress bar.

So the run is shown *starting*, honestly, with the product's own "typically 4–7
minutes" notice visible — and then the finished dossier comes from `/dossiers`,
which serves complete, unedited output captured from real runs of the deployed
service. Nothing is faked; two shots are simply separated by a cut and a caption
that says so.

## Rules constraints

- No third-party advertising, slogan, logo or trademark on screen. The stack
  ribbon uses **plain text names, not vendor logos**, partly for this reason —
  keep it that way and do not cut to any sponsor's own site or console.
- Nothing owned by a third party. Every frame of film in this video must be the
  Library of Congress public-domain demo material, on screen with its credit.
- Show it working on the platform it was built for: real browser, real URL
  visible, real latency, no speed-ramps without a caption.

## Script (voiced over screen capture)

**0:00–0:25 — the problem, at its real size**
> Of the American silent feature films ever made, fourteen percent survive in
> their original format. What does survive often arrives like this: a can with no
> name. And a film nobody can identify is not catalogued, not searchable, and not
> funded for preservation.

Screen: landing page, scroll to the **scale** section. Let the Billington pull
quote and the Mostly Lost table sit on screen — the cited numbers are the whole
argument for why this matters, and they read in two seconds.

**0:25–0:45 — why the obvious answer fails**
> A screenshot matcher only works when the answer is already in a reference set,
> which is exactly the case that does not apply. And a confident wrong answer is
> worse than none — a plausible catalogue entry propagates for thirty years.

Screen: `/presets`, scrolling the ten cases. Pause on the badges and land on the
fact that **five of the ten must not be identified**.

**0:45–1:10 — what it does instead, and what that costs**
> Five agents research. Gemini reads the frame. Parallel Search hunts the rarest
> phrase literally. Parallel Task and FindAll check alternate titles and name the
> catalogues. A Skeptic looks for evidence against its own candidates. It takes
> about six minutes, and the product says so before you start it.

Screen: press **Investigate** on D02. Hold on the run console long enough to read
the six named stages, the agent and Parallel surface on each, the live clock, and
the "typically 4–7 minutes" line. **Then cut**, with the caption:

> `A full run takes 4–7 minutes. The dossier below is the real output of this run, served from /dossiers.`

**1:10–2:00 — the part that matters**
> Then code takes over. Every citation is checked against what Parallel actually
> returned. Parallel Extract re-opens each cited page and looks for the quotation
> in the live document. This one failed — so the gate refuses it. Then a
> deterministic function counts seven thresholds, and one of them is a human.

Screen: `/dossiers`, select **D02**. Land on, in order:
1. a claim with its verified source — the LOC record for *Dud Leaves Home* (1919),
2. **the refused citation** — the single most persuasive thing in the video,
3. the seven-threshold gate, with `human_approved` failing.

Say the last point out loud: the system got this one right and still would not
assert it.

**2:00–2:20 — uncertainty as a result**
> It will not say "last surviving copy" — searching every catalogue you can name
> can never tell you no other print exists. When the evidence is not there it
> abstains. And because archives digitise continuously, it can leave a standing
> watch on the exact phrase it transcribed.

Screen: switch to **D03** in the archive — a real abstention — then the cold-case
watch control.

**2:20–2:40 — the review we could not get**
> No archivist has reviewed this. So instead of claiming otherwise, it publishes
> twelve demands that archivists have already made in print — including a
> peer-reviewed study where archive experts assessed AI cataloguing — and answers
> each one. Two are marked unanswered. The missing review is the first of them.

Screen: `/practice`. Scroll so the **Unanswered** group is on screen first, with
P5 legible. Do not scroll past it quickly; this section is the credibility of
everything before it.

**2:40–3:00 — it is a product, not a demo**
> No signup. Mint a key, call the same public endpoints, put it in your own
> catalogue tooling.

Screen: `/api` — mint a key and send one live `GET` (not an investigation; it must
return inside the shot). Close on `/stack` scrolled so several surfaces and their
call sites are visible.

## Capture checklist

- [ ] 1920×1080, browser at ~1440px wide so the stack ribbon sits on two tidy rows.
- [ ] Light theme; it reads better in compressed video than the dark one.
- [ ] URL bar visible at least once, showing the real Cloud Run domain.
- [ ] The LOC credit line legible whenever archival footage is on screen.
- [ ] No console, no editor, no cloud dashboards, no sponsor logos.
- [ ] The cut away from the running investigation carries its caption.
- [ ] The refused citation is legible at 1080p, not just visible.
- [ ] `/practice` shows an **Unanswered** entry on screen, not only answered ones.
- [ ] Captions or subtitles burned in.
- [ ] Watch it once at 3:00 exactly and confirm the close lands inside.

## What to say if asked "did you cut the wait?"

Yes, and the video says so on screen. The run in the video is real, the dossier
shown is the real output of a real run of the deployed service, and both the
measured latency distribution and every captured dossier are published:
`/v1/eval/arm-c` and `/v1/dossiers`.
