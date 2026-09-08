# Who this is for, and what the record says about them

Every number on this page is cited. Where the comparison is not fair, it says so.

## 1. The scale of the loss is settled, and it is not small

The Library of Congress commissioned a census. David Pierce's *The Survival of
American Silent Feature Films: 1912–1929* (CLIR / Library of Congress, for the
National Film Preservation Board, December 2013) found that of roughly 11,000
American silent feature films:

- **14%** — about **1,575 titles** — survive in their original format.
- **5%** of the surviving originals are incomplete.
- **11%** survive only in lower-quality formats or foreign versions.
- **26%** of survivors were found in other countries; **24%** have been repatriated.

Librarian of Congress James H. Billington, on publication:

> "The loss of American silent-era feature films constitutes an alarming and
> irreversible loss to our nation's cultural record."

Source: [CLIR and LC Publish Report on America's Endangered Silent-Film Heritage](https://www.clir.org/2013/12/clir-and-lc-publish-report-on-americas-endangered-silent-film-heritage/)

## 2. The bottleneck is not only decay. It is identification.

A reel that survives but cannot be named is not catalogued, not searchable, not
prioritised for preservation funding, and not screenable. The Library of Congress
runs an annual workshop for exactly this problem. Its own description of what
comes in is precise:

> "unidentified, under-identified or **misidentified** silent and early sound films"

Note the third category. A film catalogued under the wrong title is not a gap in
the record; it is an error *in* the record, and it will not announce itself.

Source: [Library's Cinematic Quest for "Mostly Lost" Films](https://www.loc.gov/item/prn-19-057/librarys-cinematic-quest-for-mostly-lost-films/2019-05-23/), Library of Congress, 23 May 2019

## 3. The professional method, in the profession's own words

The "Mostly Lost" workshop at the Packard Campus for Audio Visual Conservation:

> "As films roll, they shout out clues they see onscreen that might help identify
> the film and search online databases for titles that match the clues."

Source: [Recovering Silent Films: The Mostly Lost Workshop](https://blogs.loc.gov/loc/2019/01/recovering-silent-films-the-mostly-lost-workshop/), Library of Congress, January 2019

That is this system's pipeline, in that order. The VisualExaminer transcribes what
is on screen, verbatim, without guessing. The PhraseHunter takes the rarest strings
and searches them as quoted literals. The design is not a novel theory of
identification; it is an existing professional method, automated.

## 4. How hard it is, measured by the people who do it

The workshop publishes its hit rate:

| Year | Titles screened | Identified during the event |
|---|---:|---:|
| 2016 | 142 | 32 (**23%**) |
| 2017 | 180 | 52 (**29%**) |
| 2018 | 187 | 56 (**30%**) |

Further identifications follow afterwards — 46 more in 2017, 24 more in 2018 —
through the Association of Moving Image Archivists Nitrate Committee. Across seven
years the workshops identified 403 films, "just over half the number screened".

Organiser Rob Stone explains why the rate is not higher:

> "We try not to include any easy ones at the workshop, we want our Mostly Lost
> attendees to really work, and our high percentage of identifications show that
> they do just that."

Sources: [2017 release (prn-17-062)](https://www.loc.gov/item/prn-17-062/library-investigates-mostly-lost-films/2017-05-01/) · [2018 release (prn-18-050)](https://www.loc.gov/item/prn-18-050/librarys-cinematic-treasure-hunt-for-mostly-lost-films) · [2019 release (prn-19-057)](https://www.loc.gov/item/prn-19-057/librarys-cinematic-quest-for-mostly-lost-films/2019-05-23/) · [LOC blog, Jan 2019](https://blogs.loc.gov/loc/2019/01/recovering-silent-films-the-mostly-lost-workshop/)

**This is context, not a scoreboard.** Our development split is five fragments with
a sealed answer key; theirs is 187 films chosen because they are hard. The corpora
are not comparable, n=5 supports no rate at all, and no claim that this system
outperforms expert archivists is made here or anywhere else in this project. The
figures are cited for one reason: a reader should know that the people who do this
professionally, in a room together, identify well under half of what they screen.
Anyone promising near-certainty on this task is selling something.

## 5. What is actually different here

Not accuracy. Three things about *availability*.

**It runs between workshops.** Mostly Lost happens once a year, over four days, in
Culpeper, Virginia. An archive that finds an unlabelled can in October waits.
This runs on request, from anywhere, through an API with a key anyone can mint.

**It produces a dossier, not an answer.** The output is the evidence: every claim,
every source, which sources were re-opened and confirmed on the live page, which
of seven thresholds passed, and what is still unresolved. An archivist can audit
it in minutes and disagree with it specifically. That is a different artifact from
a title and a confidence score, and it is the artifact the ArchiveGPT study
concluded practitioners need — AI "subordinate to human verification".

**A cold case can stay open.** Identification is not a one-shot task; evidence
appears later. When an investigation ends without an identity, the system can open
a Parallel Monitor on the rare strings it transcribed, checked weekly and
indefinitely. If a digitised trade paper carrying that exact intertitle is
published in 2027, the fragment's file is the thing that gets updated. No annual
workshop can do that, and it is the part of this design that is genuinely not a
faster version of what humans already do.

## 6. Who would use it

The archives that already send material to Mostly Lost are named in the Library's
own releases: the George Eastman Museum, EYE Filmmuseum, the Museum of Modern Art,
UCLA, Lobster Films, the Cinémathèque Française, and the Packard Humanities
Institute. They are the audience. The API needs no signup, no email, and no
commercial relationship, and the evaluation corpus is public Library of Congress
material so anyone can check the results against the same fragments we used.

## 7. What this does not do

- **No archivist has reviewed it.** See `/v1/practice`, entry P5, marked `not_met`.
  Every claim on this page about usefulness is inference from published practice,
  not observation of a practitioner using it.
- It does not replace the workshop, which does things a pipeline cannot: recognise
  a face, place a street, or remember a print seen thirty years ago.
- It is measured on five fragments. Five is enough to show a mechanism works and
  nowhere near enough to state a rate.
- It abstained on one case it should have identified (D04), and a citation-strictness
  rule cost it that identification. That trade is deliberate and it is a real cost.
