# Demo video — shot list and script

Hard limit **3 minutes**; only the first three are evaluated. Public on YouTube
or Vimeo. English, or English subtitles.

**Record it only after `/health/integrations` reports Parallel live.** A video of
the fail-closed state would show the product refusing to work, which is honest
but is not what three minutes should be spent on.

## Rules constraints that shape the edit

- No third-party advertising, slogan, logo or trademark on screen. The stack
  ribbon uses **plain text names, not vendor logos**, partly for this reason —
  keep it that way and do not cut to any sponsor's own site or console.
- Nothing owned by a third party. Every frame of film in this video must be the
  Library of Congress public-domain demo material, on screen with its credit.
- Show it *working on the platform it was built for*: real browser, real URL
  visible, real latency. Do not speed up an investigation without saying so.

## Script (voiced over screen capture)

**0:00–0:20 — the problem**
> Film archives hold material nobody can name. This is a fifty-second fragment
> from the Library of Congress. No title card, no paperwork.

Screen: the landing page, then scroll to the illustrated frame. Let the demo
video on `/presets` play for two or three seconds so real archival footage is on
screen with its credit line visible.

**0:20–0:40 — why the obvious answer fails**
> A screenshot matcher only works when the answer is already in a reference set.
> That is exactly the case that does not apply here. And a confident wrong answer
> is worse than none: a plausible catalogue entry propagates for thirty years.

Screen: `/presets`, scrolling the ten cases. Pause on the badges — land on the
fact that **five of the ten must not be identified**.

**0:40–1:10 — what it does instead**
> Five agents research. Gemini reads the frame. Parallel Search hunts the rarest
> phrase literally. Parallel Task and FindAll check alternate titles and name the
> catalogues. A Skeptic looks for evidence against its own candidates.

Screen: press **Investigate** on D02 and let the run console play. This is the
shot the console was designed for — six named stages, each showing which agent
and which Parallel surface, with a real clock. Do not cut away from it; it is
the clearest explanation of the architecture in the whole video.

**1:10–1:55 — the part that matters**
> Then code takes over. Every citation is checked against what Parallel actually
> returned. Then Parallel Extract re-opens each cited page and looks for the
> quotation in the live document — this one failed, so the gate refuses it. And a
> deterministic function counts seven thresholds.

Screen: the dossier. Land on, in order:
1. a claim with its verified source,
2. **the refused citation** — the single most persuasive thing on screen,
3. the seven-threshold gate with its passes and failures.

**1:55–2:20 — uncertainty as a result**
> It will not say "last surviving copy" — searching every catalogue you can name
> can never tell you no other print exists. And when the evidence is not there it
> abstains, then leaves a standing watch, because archives digitise continuously.

Screen: run **D01**, the abstention case, or cut to it prepared. Show the abstain
verdict and the cold-case watch button.

**2:20–2:50 — it is a product, not a demo**
> No signup. The page mints itself a real API key and calls the same public
> endpoints you would. Bring your own fragment, or put it in your own catalogue
> tooling.

Screen: `/api` — mint a key, send one live request, show the response. Then the
upload tab for two seconds.

**2:50–3:00 — close**
> Triage, not attribution. An archivist approves every identification. This page
> never does.

Screen: `/stack`, scrolled so several surfaces and their call sites are visible.

## Capture checklist

- [ ] 1920×1080, browser at ~1440px wide so the stack ribbon sits on two tidy rows.
- [ ] Light theme; it reads better in compressed video than the dark one.
- [ ] URL bar visible at least once, showing the real Cloud Run domain.
- [ ] The LOC credit line legible whenever archival footage is on screen.
- [ ] No console, no editor, no cloud dashboards, no sponsor logos.
- [ ] Investigation timings real, or a caption saying the wait was trimmed.
- [ ] Captions or subtitles burned in.
- [ ] Watch it once at 3:00 exactly and confirm the close lands inside.
