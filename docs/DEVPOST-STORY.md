## Inspiration

Film archives hold reels nobody can name. A can with no label, a donation whose paperwork was lost decades ago, a print spliced from three others.

The scale is settled and it is not small. The Library of Congress commissioned a census, and it found that **only 14% of American silent feature films survive in their original format**, about 1,575 of roughly 11,000 ([David Pierce, *The Survival of American Silent Feature Films: 1912–1929*, CLIR / Library of Congress, 2013](https://www.clir.org/2013/12/clir-and-lc-publish-report-on-americas-endangered-silent-film-heritage/)). Librarian of Congress James H. Billington called it "an alarming and irreversible loss to our nation's cultural record."

But survival is not the whole problem. A reel that exists and cannot be named is not catalogued, not searchable, and not funded for preservation. The Library runs a workshop every year for exactly this, where historians sit in a room and shout out clues, and it publishes its own hit rate: **23%, 29% and 30%** of the films screened in 2016, 2017 and 2018 ([Mostly Lost, Library of Congress](https://www.loc.gov/item/prn-19-057/librarys-cinematic-quest-for-mostly-lost-films/2019-05-23/)). That is the state of the art, and it happens four days a year in Virginia.

So the question we built for was not "can a model identify this film". Almost every AI answer here is a screenshot matcher, which works only when the answer is already in a reference set, which is precisely the case that does not apply to unidentified material. And the dangerous failure is not a wrong answer, it is a **plausible** one: a catalogue entry that looks researched, propagates for thirty years, and quietly misattributes a film.

The question was: **can a system show its evidence honestly enough that an archivist can act on it?**

## What it does

Send a fragment: one of ten public-domain Library of Congress clips, or your own file. You get back a **dossier, not an answer**.

- **Every claim with the source behind it**, and the exact quoted excerpt.
- **The contradictions found against its own leading candidate**, shown next to the evidence for it.
- **Which citations were refused**, and why. Every cited page is re-opened and checked for the exact quoted words; a search snippet is a summary of a page, this is the page itself.
- **Nine thresholds**, each shown whether it passed or failed, so you can see exactly what was missing.
- **A verdict that can be "I don't know."** Abstaining is a correct outcome, not a failure.
- **A standing watch.** When a fragment stays unidentified, it can leave a weekly query on the rare strings visible in the frame, because archives digitise continuously and an abstention is the right answer today and the wrong answer forever.

**The strongest thing it can return is "candidates".** A probable identity requires an archivist's approval, which is one of the nine thresholds and which no API call can satisfy. The system cannot assert an identity even when it is right.

Everything is usable without an account: **watch and download all ten fragments**, read complete dossiers from real runs, **upload your own footage**, or mint a 60-day API key with no email and call the same endpoints the site calls.

## How we built it

**Google Cloud.** A five-role [Google ADK](https://google.github.io/adk-docs/) workflow on **Gemini 2.5 Flash** via Vertex AI: a Visual Examiner that transcribes what is on screen without guessing, a Phrase Hunter, a Holdings Researcher, a Skeptic whose only job is to attack the candidate, and an Evidence Compiler that restates everything as typed claims using controlled generation. Cloud Run hosts it; Secret Manager holds the credentials.

**Parallel, all six surfaces, each with a distinct job.** Search hunts the rarest visible phrases as literal quoted strings. Task researches alternate titles and holdings against an archival source policy. FindAll runs a census of named catalogues. **Extract re-opens every cited page to confirm the quotation is really there.** Task Group fans out one independent run per candidate whose only purpose is to disprove it. Monitor keeps the cold case open.

**Then ordinary code takes over.** A citation registry discards any URL Parallel did not actually return in that run, and marks any excerpt it cannot find in the retrieved text. A deterministic gate counts the nine thresholds. The model gathers evidence; **it never decides what the evidence is worth**.

We also checked the design against the standard the intended users already work to, the [FIAF Moving Image Cataloguing Manual (2016)](https://www.fiafnet.org/pages/E-Resources/Cataloguing-Manual.html), and published seven page-cited requirements with how each is met. One was failing: FIAF A.2.5 says an unidentifiable item should still receive a supplied title so it can be filed and found. Abstentions returned no title at all. That is fixed.

## Challenges we ran into

**FindAll is asynchronous, and we were blocking on it.** Parallel's own console says a census takes 5 to 60 minutes. Our first live run simply hung. It now commissions the census, returns a handle immediately, and you collect the result separately.

**A four-minute partner call is not a research budget, it is a timeout.** We benchmarked Task processors against our own schema on a real question: `lite` 57s, `base` 69s, `core` 79s, `pro-fast` 268s, for output that was longer but no better sourced. We use `base`.

**The interface lied about how long a run takes, twice.** The run console's stage timings were written from a pre-credential estimate totalling 100 seconds. The real median is 304s. Nothing crashed; the console simply walked through all six stages in under two minutes and then sat on the last one for four more, which is exactly the hang-reading it exists to prevent.

**And the hardest one: our headline did not survive being re-run.** Our first measured pass recorded two correct identities and zero false-confident identifications. Repeating it disagreed. So we ran it again, and again.

## Accomplishments that we're proud of

**We ran the same five fragments 28 times and published every run, including the ones that went badly.**

| Across 28 runs | |
|---|---:|
| Cases giving the same verdict every time | **1 of 5** |
| Correct identities | 3 |
| **Named the wrong film** | **9** |
| Candidates that were not a film at all | 7 |
| **Ever claimed a probable identity** | **0** |

One case returned four different leading candidates in four runs. Another returned the same wrong film three times out of four. Our published "zero false-confident identifications" was one lucky pass.

We could have shipped the good pass and said nothing. Publishing it is the only position consistent with what the product argues, **a system that asks an archivist to trust it cannot hide the runs where it was wrong**, and it is served from our own API at `/v1/eval/stability`, not buried in a footnote.

And the one property that held across all 28 runs: **it never once claimed a probable identity.** Every wrong answer arrived as "candidates" with its failing thresholds attached. That is a weaker claim than "never wrong", and it is the true one.

**We also could not get an archivist to review it**, so rather than pretend otherwise we published 14 demands that archivists and analysts have already made in print, each quoted and answered, and marked the four we do not meet, starting with the missing review itself.

## What we learned

**Confirmation bias is structural, not a prompt problem.** When we read the failing runs, one case had produced exactly one candidate and then agreed with it fourteen times. Nothing ever competed with it, so no amount of evidence could discriminate. That is the failure [Richards Heuer's Analysis of Competing Hypotheses](https://onlinelibrary.wiley.com/doi/full/10.1002/acp.3550) was designed for at the CIA, and it is documented in current LLM work: ["Failing to Falsify" (Jhaveri et al., arXiv:2604.02485)](https://arxiv.org/abs/2604.02485) finds that confirmation bias in exploratory reasoning "manifests not in how evidence is interpreted, but in how evidence is *selected*." The gate now requires a rival hypothesis and evidence that actually discriminates between them.

**A fix can be real and still not work.** We shipped it and measured again. Candidates that named no film went from 7 to 0, but that is true by construction, since the filter removes them. False-confident identifications did **not** improve. The observations showed why: when the pipeline had no answer it used to write down a studio or a costume period, which scored as neither right nor wrong. Constrain the type, and it writes down a real film instead, usually the wrong one. **The candidate slot was a pressure valve, and we changed what came out of it rather than closing it.** The error rate was always about this high; the malformed answers were hiding it.

**Practitioners are ahead of us.** [ArchiveGPT (Abele et al., arXiv:2507.07551)](https://arxiv.org/abs/2507.07551) put AI-generated catalogue descriptions in front of archive experts and found "OCR errors and hallucinations limited perceived quality", that human review remains necessary, and that adoption depends less on model quality than on "a transparent and explainable AI pipeline". Every one of those objections predates this project and shaped it.

## What's next for Last Seen Alive

**An archivist.** One professional, one day, running the five development fragments and recording where the dossiers helped and where they wasted their time. Nothing in the code substitutes for it.

**The sealed holdout.** Five fragments the system has never been run on, whose hashes are already published so the set cannot be quietly changed. It gets opened exactly once, and every miss gets published beside every success.

**Closing the pressure valve.** "No candidate" needs to be a first-class output the compiler is asked for, rather than an absence it falls into. Right now we tell the model what a candidate may not be; nothing yet tells it that returning none is a correct and expected result.
