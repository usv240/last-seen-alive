# Demo video — shot list and script

Hard limit **3 minutes**; only the first three are evaluated. Public on YouTube
or Vimeo. English, or English subtitles.

**Record it only after `/health/integrations` reports Parallel live.** A video of
the fail-closed state would show the product refusing to work, which is honest
but is not what three minutes should be spent on.

## The constraint that shapes this edit

An investigation takes **61–430 seconds**, median 299 across 18 measured runs —
published at `/v1/eval/stability` and stated on screen by the product itself.
**You cannot rely on showing a complete live run inside a three-minute video**: the
median is five minutes and one recorded run took ninety-five. An earlier version of this script
said "let the run console play, do not cut away from it". That is no longer
possible and pretending otherwise would mean either faking a fast run or spending
the entire video on a progress bar.

So the run is shown *starting*, honestly, with the product's own "usually 1–8
minutes; the median of 18 measured runs is 5" notice visible — and then the finished dossier comes from `/dossiers`,
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
> about five minutes, and the product says so before you start it.

Screen: press **Investigate** on D04. Hold on the run console long enough to read
the six named stages, the agent and Parallel surface on each, the live clock, and
the measured-duration line. **Then cut**, with the caption:

> `A run takes about five minutes. The dossier below is real output from a real run of this service, served from /dossiers.`

**1:10–2:00 — the part that matters, on a case it got wrong**
> Then code takes over. Every citation is checked against what Parallel actually
> returned. Parallel Extract re-opens each cited page and looks for the quotation
> in the live document. This one failed, so the gate refuses it. Then a
> deterministic function counts seven thresholds — and one of them is a human.

Screen: `/dossiers`, select **D04** — 14 claims, 11 confirmed sources, **one
refused citation**, five of seven thresholds. Land on, in order:
1. a claim with its verified source,
2. **the refused citation** — the single most persuasive thing in the video,
3. the seven-threshold gate, with `human_approved` and
   `unresolved_contradictions==0` failing.

Then say the uncomfortable part out loud, because it is the strongest thing here:

> Its leading candidate is *Un coin de Paris*, from 1900. The answer key says
> *Buying a cow*, from 1908. It is wrong — and it does not get to say so. It hands
> over the evidence, marks the citation it could not confirm, and stops.

**Do not swap this for a success.** The captured D04 dossier is the only one that
carries a refused citation, and a demo that shows the machine being wrong safely
is worth more than one that shows it being right. Verify the shot against the live
page before recording: the dossiers are real runs and a future recapture may move.

**2:00–2:25 — the part most demos leave out**
> We ran those five fragments nineteen times. Only one of the five gave the same
> verdict every time. One case returned four different answers in four runs.
> Another returned the same wrong film three times out of four. Zero
> false-confident identifications was true of one pass, not of this system —
> across nineteen runs there are five.

Screen: the landing page's 19-run table, then `/v1/eval/stability` raw JSON for a
beat so it is clear the number is served, not asserted.

> What did hold: no run, in nineteen, ever claimed a probable identity. That
> needs a human, and the API cannot supply one.

**2:25–2:45 — the review we could not get**
> No archivist has reviewed this. So instead of claiming otherwise, it publishes
> fourteen demands archivists and analysts have already made in print — including a peer-reviewed
> study where archive experts assessed AI cataloguing — and answers each one.
> Four are unanswered or only partly answered. The missing review is the first.

Screen: `/practice`. Scroll so the **Unanswered** group is on screen first, with
P5 legible. Do not scroll past it quickly; this section, and the one before it,
are the credibility of everything else in the video.

**2:45–3:00 — it is a product, not a demo**
> No signup. Mint a key, call the same public endpoints, put it in your own
> catalogue tooling. Triage, not attribution — an archivist approves every
> identification, and this page never does.

Screen: `/api` — mint a key and send one live `GET` (not an investigation; it must
return inside the shot). Close on `/stack`.

## Capture checklist

- [ ] 1920×1080, browser at ~1440px wide so the stack ribbon sits on two tidy rows.
- [ ] Light theme; it reads better in compressed video than the dark one.
- [ ] URL bar visible at least once, showing the real Cloud Run domain.
- [ ] The LOC credit line legible whenever archival footage is on screen.
- [ ] No console, no editor, no cloud dashboards, no sponsor logos.
- [ ] The cut away from the running investigation carries its caption.
- [ ] The refused citation is legible at 1080p, not just visible.
- [ ] `/practice` shows an **Unanswered** entry on screen, not only answered ones.
- [ ] The 19-run stability table is legible at 1080p. Do not cut it for time; cut
      the prior-art or upload shots instead.
- [ ] Captions or subtitles burned in.
- [ ] Watch it once at 3:00 exactly and confirm the close lands inside.

## What to say if asked "did you cut the wait?"

Yes, and the video says so on screen. The run in the video is real, the dossier
shown is the real output of a real run of the deployed service, and the measured
latency distribution, every captured dossier, and every recorded run — including
the ones that went badly — are published: `/v1/eval/stability`, `/v1/dossiers`.

## What to say if asked "why show your own failures?"

Because the alternative is a system that asks archivists to trust an identification
while hiding that the same fragment gave a different answer on the previous run.
The 19-run study is the most persuasive thing in the submission precisely because
nobody would publish it unless they meant the rest.
