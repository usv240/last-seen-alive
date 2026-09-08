# Demo script — read this while recording

**3:00 hard limit.** Only the first three minutes are judged. The narration below
is **418 words — about 2:47** at a normal pace, leaving ~13 seconds for the
visuals to land. That margin is thin: if you speak slowly, use the cut list at
the bottom rather than rushing the two beats that matter.

Open two tabs before you start:
1. `https://last-seen-alive-109051079423.us-central1.run.app`
2. the same URL at `/dossiers#D04`

---

## Why this script is shaped this way

The video is **not** a scored category. Rules.md §8 gives four **equal-weighted**
criteria — Technological Implementation, Design, Potential Impact, Quality of the
Idea — at 25% each. The video is a Stage One pass/fail requirement *and* the only
thing most judges will ever actually see. So it is not 30% of your score; it is
the lens all 100% is judged through.

Every beat below is tagged with the criterion it is buying. Nothing is in here
that does not buy one.

---

## 0:00–0:22 · The problem
**Buys: Potential Impact**

**NAVIGATE:** Landing page. Scroll to the section headed *"Most of it is already
gone."*
**POINT AT:** the Billington pull quote, then the Mostly Lost table (23% / 29% / 30%).

> **"Seventy percent of American silent films are gone. What survived often
> arrives like this — a can with no name. Every year the Library of Congress fills
> a room with historians who shout out clues to identify them. They get under a
> third. That is the state of the art."**

*Do not rush this. The cited numbers are the entire argument for why the project
matters, and they read in two seconds.*

---

## 0:22–0:40 · Why it is hard
**Buys: Quality of the Idea**

**NAVIGATE:** `/presets`
**POINT AT:** the outcome badges — scroll so several are visible at once.

> **"Ten Library of Congress fragments. Only four should be identified. For the
> other six the right answer is 'I don't know', or a list, or a correction to the
> label it came with. A confident wrong answer is worse than none — a bad
> catalogue entry propagates for thirty years."**

---

## 0:40–1:05 · Start a real run
**Buys: Technological Implementation**

**NAVIGATE:** back to the landing page, section *"Run a public fragment"*.
**DO:** select **D04** and press **Investigate**.
**POINT AT:** the six stages as they light up — each names its agent and its
Parallel surface — then the live clock and the duration line.

> **"Five agents. Gemini transcribes the frame word for word. Parallel Search
> hunts the rarest phrase as a literal quote. Parallel Task and FindAll check
> alternate titles and name the archives holding them. A Skeptic hunts evidence
> against its own answer. Five minutes — and it tells you that up front."**

**CUT HERE.** On-screen caption:

> `A full run takes ~5 minutes. The dossier below is real output from a real run of this service.`

---

## 1:05–1:50 · The dossier — first wow
**Buys: Technological Implementation + Design**

**NAVIGATE:** `/dossiers`, click **D04**.
**POINT AT, in this order:**
1. a claim with its confirmed source,
2. **the refused citation** — hold on this,
3. the threshold panel, with `human_approved` failing.

> **"Then code takes over. Every citation is re-opened by Parallel Extract and
> checked against the live page. This one failed — so the gate refuses it. It
> counts toward nothing."**

> **"Now the part I want you to see. Its leading candidate is 'Un coin de Paris',
> 1900. The answer key says 'Buying a cow', 1908. It is wrong."**

> **"And it does not get to say so. It hands over the evidence, marks what it
> could not confirm, and stops."**

---

## 1:50–2:20 · The stability study — the wow that wins it
**Buys: Quality of the Idea, and the credibility of everything above**

**NAVIGATE:** landing page, section *"We measured the alternative before we
measured ourselves."* Scroll to the **19-run table**.
**THEN:** open `/v1/eval/stability` for two seconds of raw JSON.

> **"We ran these same five fragments nineteen times. Only one gave the same
> verdict every time. Our own published headline — zero false-confident
> identifications — was one lucky pass. Across nineteen runs there are five."**

> **"That is on our own landing page. A system asking an archivist to trust it
> cannot hide the runs where it was wrong."**

> **"One thing held. In nineteen runs it never once claimed a probable identity —
> that needs a human, and the API cannot supply one."**

*This is the single most memorable thirty seconds in the video. Judges watch
polished demos all day. They almost never see a team show them the failures.*

---

## 2:20–2:40 · The review we could not get
**Buys: Potential Impact**

**NAVIGATE:** `/practice`
**POINT AT:** the **Unanswered** group — it renders first, above everything the
system does well. Make sure P5 is legible.

> **"No archivist has reviewed this. So rather than pretend otherwise, we took
> fourteen demands archivists have already published — including a peer-reviewed
> study where archive experts graded AI cataloguing — and answered each one. Four
> are unanswered. The missing review is first."**

---

## 2:40–3:00 · It is a product, not a demo
**Buys: Design + Technological Implementation**

**NAVIGATE:** `/api`. Press **Mint a judge key**. Send one `GET /v1/stack`.
**THEN:** `/stack`, scrolled so several surfaces and their call sites show.

> **"No signup. Mint a key, call the same endpoints this page calls, put it in
> your own catalogue. Eleven sponsor surfaces, each with the line of code that
> calls it."**

> **"Triage, not attribution. An archivist approves every identification. This
> page never does."**

---

## Capture checklist

- [ ] 1920×1080. Browser ~1440px wide so the stack ribbon sits on two tidy rows.
- [ ] **Light theme** — reads better than dark once the video is compressed.
- [ ] URL bar visible at least once showing the real Cloud Run domain.
- [ ] The Library of Congress credit line legible whenever footage is on screen.
- [ ] No terminal, no editor, no cloud consoles, **no sponsor logos** (Rules.md
      forbids third-party marks — our ribbon is plain text on purpose).
- [ ] The cut away from the running investigation carries its caption.
- [ ] The **refused citation** is legible, not just visible.
- [ ] The **19-run table** is legible. If you are over time, cut the `/api` beat
      before you cut this one.
- [ ] English subtitles burned in.
- [ ] Upload to YouTube or Vimeo, **public**, and paste the link into Devpost.

## If you are running long

Cut in this order. Never cut from the top of the list.

1. The `/api` mint-a-key beat (2:40) — keep only the `/stack` close.
2. The `/practice` beat (2:20) — painful, but the stability study makes the same
   point about honesty.
3. Trim the `/presets` beat (0:22) to one sentence.

**Never cut:** the refused citation, or the 19-run table. Those two are the
submission.

## Before you hit record

Check the D04 dossier still shows a refused citation — the dossiers are captured
from real runs and a recapture can move them. It is there as of the last check.
Fuller production notes, including the rules constraints, are in
[`DEMO-VIDEO.md`](DEMO-VIDEO.md).
