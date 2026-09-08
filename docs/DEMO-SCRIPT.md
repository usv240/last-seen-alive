# Demo script — read this while recording

**Target a finished video of 2:45–2:50, not 2:59.** The limit is 3:00 and anything
past it is not evaluated, so aiming at the line risks losing the ending. The
narration below is **399 words — about 2:40** spoken normally. With the two
scripted pauses that lands at **2:44**, leaving ~16 seconds for navigation. Those
pauses are part of the script, not slack. **Do not fill them.**

Open two tabs before you start:
1. `https://last-seen-alive-109051079423.us-central1.run.app`
2. the same URL at `/dossiers#D04`

---

## Why this script is shaped this way

The video is **not** a scored category. Rules.md §8 gives four **equal-weighted**
criteria — Technological Implementation, Design, Potential Impact, Quality of the
Idea — at 25% each. The video is a Stage One pass/fail requirement *and* the only
thing most judges will ever actually see. It is not a slice of your score; it is
the lens the whole score is formed through.

Every beat is tagged with the criterion it buys. Two rules govern the whole thing:

**The judge must know what this is by 0:25.** Everything after that is then proof
of one sentence, rather than a mystery that resolves at 1:30.

**The technology supports the story; it must not become the story.** A judge who
remembers "Gemini plus six Parallel APIs" has remembered a checklist. A judge who
remembers "the AI was wrong and the architecture stopped it" has remembered the
submission.

---

## 0:00–0:25 · The problem, then what you built
**Buys: Potential Impact**

**NAVIGATE:** Landing page. Scroll to the section headed *"Most of it is already
gone."*
**POINT AT:** the Billington pull quote, then the Mostly Lost table (23% / 29% / 30%).

> **"Seventy percent of American silent films are gone. What survived often
> arrives like this — a can with no name. Every year the Library of Congress fills
> a room with historians who shout out clues to identify them. They get under a
> third."**

**POINT AT:** the page title as you say the next line.

> **"Last Seen Alive turns an unidentified fragment into an evidence dossier — and
> when the evidence isn't strong enough, it refuses to identify the film."**

*That second sentence is the whole product. Say it clearly and a little slower
than the rest. Every beat after this is proof of it.*

---

## 0:25–0:42 · Why it is hard
**Buys: Quality of the Idea**

**NAVIGATE:** `/presets`
**POINT AT:** the outcome badges — scroll so several are visible at once.

> **"Ten Library of Congress fragments. Only four should be identified. For the
> other six the right answer is 'I don't know', or a list, or a correction to the
> label it came with. A confident wrong answer is worse than none — a bad
> catalogue entry propagates for thirty years."**

---

## 0:42–1:05 · Start a real run
**Buys: Technological Implementation**

**NAVIGATE:** landing page, section *"Run a public fragment"*.
**DO:** select **D04** and press **Investigate**.
**POINT AT:** the six stages as they light up — each names its agent and its
Parallel surface — then the live clock and the duration line.

> **"Five agents, one workflow: extract the clues, research the evidence, attack
> its own hypothesis, verify every citation, then gate the conclusion. Gemini
> reads the frame. Parallel Search, Task and FindAll do the research. It takes
> about five minutes, and it tells you that before you start."**

*Say the workflow verbs and let the screen name the services. The stages already
show which agent calls which Parallel surface, so reciting all six aloud buys
nothing and costs ten seconds. This is how you earn Technological Implementation
without sounding like a sponsor list.*

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
> checked against the live page. This one failed — so the gate refuses it."**

> **"Now the part I want you to see. Its leading candidate is 'Un coin de Paris',
> 1900. The answer key says 'Buying a cow', 1908. It is wrong."**

### ⏸ PAUSE — two full seconds. Let the wrong answer sit on screen.

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

### ⏸ PAUSE — two full seconds on the number 5.

> **"A system asking an archivist to trust it cannot hide the runs where it was
> wrong. In nineteen runs it never once claimed a probable identity — that needs
> a human, and the API cannot supply one."**

*The most memorable thirty seconds in the video. Judges watch polished demos all
day; they almost never see a team show them the failures.*

---

## 2:20–2:32 · The review we could not get
**Buys: Potential Impact**

**NAVIGATE:** `/practice`
**POINT AT:** the **Unanswered** group — it renders first, above everything the
system does well.

> **"No archivist has reviewed this yet. We say that plainly, and we publish the
> practitioner requirements the system still doesn't meet."**

*Deliberately short. By 2:20 the judge already believes you are honest, because
the stability study proved it. Showing the page is enough; explaining the register
costs ten seconds that D04 and the 19-run table need more.*

---

## 2:32–2:50 · Close on the human, not the stack
**Buys: Design + Technological Implementation + Potential Impact**

**NAVIGATE:** `/api`, press **Mint a judge key**, send one `GET /v1/stack`.
**THEN:** `/stack`, scrolled so several surfaces and their call sites show. Leave
it on screen for the final line.

> **"No signup. Mint a key and call the same endpoints this page calls. Eleven
> sponsor surfaces, each with the line of code that calls it."**

> **"The archivist still makes the identification. Last Seen Alive makes sure they
> don't start from an unidentified reel and a blank page."**

*End on the person, not the architecture. The stack stays on screen so the
technical claim is visible while the human claim is spoken — you get both without
spending words on either.*

---

## Capture checklist

- [ ] 1920×1080. Browser ~1440px wide so the stack ribbon sits on two tidy rows.
- [ ] **Light theme** — reads better than dark once the video is compressed.
- [ ] URL bar visible at least once showing the real Cloud Run domain.
- [ ] The Library of Congress credit line legible whenever footage is on screen.
- [ ] No terminal, no editor, no cloud consoles, **no sponsor logos** (Rules.md
      forbids third-party marks — our ribbon is plain text on purpose).
- [ ] The cut away from the running investigation carries its caption.
- [ ] **Both pauses are actually in the edit.** Check on playback.
- [ ] The **refused citation** is legible, not just visible.
- [ ] The **19-run table** is legible.
- [ ] English subtitles burned in.
- [ ] Finished length **2:45–2:50**. If it lands at 2:58, cut — do not ship it.
- [ ] Upload to YouTube or Vimeo, **public**, link into Devpost.

## If you are running long

Cut in this order. Never cut from the top of the list.

1. The mint-a-key sentence at 2:32 — keep the `/stack` visual and the closing line.
2. The `/practice` beat (2:20) entirely — the stability study already made the
   point about honesty.
3. Trim the `/presets` beat (0:25) to one sentence.

**Never cut:** the thesis sentence at 0:20, the refused citation, the 19-run
table, or the two pauses. Those four are the submission.

## Before you hit record

Check the D04 dossier still shows a refused citation — the dossiers are captured
from real runs and a recapture can move them. It is there as of the last check.
Fuller production notes, including the rules constraints, are in
[`DEMO-VIDEO.md`](DEMO-VIDEO.md).
