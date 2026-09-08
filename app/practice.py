"""What practitioners have published about this problem, and how this system answers.

No archivist has reviewed this project. That is the honest ceiling on every claim
it makes, and a hackathon deadline will not lift it. What *can* be done is to stop
treating the gap as unfillable and go and read what archivists have already
published -- about the scale of the loss, about how identification actually works
in their institutions, and about what they said when researchers put an AI
cataloguing system in front of them and asked what they thought of it.

That last one matters most. ArchiveGPT (Abele et al.) is a peer-reviewed,
human-centered evaluation in which archive and archaeology experts assessed
machine-generated catalogue descriptions. Their objections are on the record. They
are not our objections, invented and then conveniently answered; they were raised
by domain experts about a system that is not ours, before this project existed.

So this module is a register. Each entry is a demand made in a published source,
quoted, cited, and paired with the specific mechanism in this system that answers
it -- or with an admission that nothing here answers it. Entries marked `not_met`
are the point of the exercise. A register with no failures would be marketing.

Every quotation here is verbatim from the cited source. Nothing is paraphrased
into a quotation, and no practitioner is represented as having reviewed, endorsed
or even heard of this project.
"""

from __future__ import annotations

from typing import Any, Literal

Status = Literal["met", "partially_met", "not_met"]

#: Sources are listed once and referenced by key, so a citation cannot drift
#: between entries.
SOURCES: dict[str, dict[str, str]] = {
    "archivegpt": {
        "citation": (
            "Line Abele, Gerrit Anders, Tolgahan Aydin, Jurgen Buder, Helen Fischer, "
            "Dominik Kimmel and Markus Huff, 'ArchiveGPT: A human-centered evaluation of "
            "using a vision language model for image cataloguing', arXiv:2507.07551 "
            "(July 2025); published in Humanities and Social Sciences Communications (2026)."
        ),
        "url": "https://arxiv.org/abs/2507.07551",
        "kind": "peer_reviewed_study",
        "why_it_counts": (
            "Archive and archaeology experts evaluated machine-generated catalogue "
            "descriptions in a controlled study. It is the closest thing in the "
            "literature to the archivist review this project cannot obtain."
        ),
    },
    "fiaf": {
        "citation": (
            "The FIAF Moving Image Cataloguing Manual, Linda Tadic (ed.), "
            "International Federation of Film Archives, 2016."
        ),
        "url": "https://www.fiafnet.org/pages/E-Resources/Cataloguing-Manual.html",
        "kind": "professional_standard",
        "why_it_counts": (
            "The cataloguing standard the intended users already work to. Conformance "
            "is tested separately and published at /v1/standards."
        ),
    },
    "mostly_lost_2019": {
        "citation": (
            "Library's Cinematic Quest for Mostly Lost Films, Library of Congress "
            "press release, 23 May 2019 (prn-19-057)."
        ),
        "url": "https://www.loc.gov/item/prn-19-057/librarys-cinematic-quest-for-mostly-lost-films/2019-05-23/",
        "kind": "national_archive_practice",
        "why_it_counts": (
            "The Library of Congress runs an annual workshop that does exactly this "
            "task, by hand, with experts in a room. It is the human process this "
            "system automates, and it publishes its own hit rate."
        ),
    },
    "mostly_lost_blog": {
        "citation": (
            "Recovering Silent Films: The Mostly Lost Workshop, Library of Congress "
            "blog, January 2019, quoting workshop organiser Rob Stone."
        ),
        "url": "https://blogs.loc.gov/loc/2019/01/recovering-silent-films-the-mostly-lost-workshop/",
        "kind": "national_archive_practice",
        "why_it_counts": "Describes the method the workshop uses, in the organiser's own words.",
    },
    "heuer_ach": {
        "citation": (
            "Richards J. Heuer Jr., 'Psychology of Intelligence Analysis', Center for the Study "
            "of Intelligence, CIA, 1999, chapter 8: Analysis of Competing Hypotheses; evaluated "
            "in Mandeep K. Dhami, Ian K. Belton and David R. Mandel, 'The \"analysis of competing "
            "hypotheses\" in intelligence analysis', Applied Cognitive Psychology 33(6), 2019."
        ),
        "url": "https://onlinelibrary.wiley.com/doi/full/10.1002/acp.3550",
        "kind": "professional_standard",
        "why_it_counts": (
            "The structured analytic technique adopted by the intelligence community for "
            "identification under uncertainty -- the same shape of problem, with the same "
            "failure mode this system was found to have."
        ),
    },
    "failing_to_falsify": {
        "citation": (
            "Ayush Rajesh Jhaveri, Anthony GX-Chen, Ilia Sucholutsky and Eunsol Choi, 'Failing "
            "to Falsify: Evaluating and Mitigating Confirmation Bias in Language Models', "
            "arXiv:2604.02485."
        ),
        "url": "https://arxiv.org/abs/2604.02485",
        "kind": "peer_reviewed_study",
        "why_it_counts": (
            "Measures confirmation bias in language models during hypothesis exploration, which "
            "is exactly the stage where this pipeline was failing."
        ),
    },
    "pierce_2013": {
        "citation": (
            "David Pierce, 'The Survival of American Silent Feature Films: 1912-1929', "
            "Council on Library and Information Resources and the Library of Congress, "
            "commissioned by the National Film Preservation Board, December 2013."
        ),
        "url": "https://www.clir.org/2013/12/clir-and-lc-publish-report-on-americas-endangered-silent-film-heritage/",
        "kind": "national_archive_practice",
        "why_it_counts": "The census that establishes the size of the problem.",
    },
}


REGISTER: list[dict[str, Any]] = [
    {
        "id": "P1",
        "source": "archivegpt",
        "demand": "AI output must remain subordinate to human verification, not replace it.",
        "quote": (
            "These findings advocate for a collaborative approach where AI supports draft "
            "generation but remains subordinate to human verification, ensuring alignment "
            "with curatorial values (e.g., provenance, transparency)."
        ),
        "how_this_system_answers": (
            "human_approved is one of the seven identity-gate thresholds and nothing in "
            "the API can satisfy it. The probable verdict is therefore unreachable through "
            "the API by construction, not by policy: the strongest thing a caller can "
            "receive is candidates with the evidence attached. The system cannot assert "
            "an identity even when it is right, which is what happened on D02."
        ),
        "evidence": ["app/gates/identity.py", "/v1/eval/arm-c", "/v1/example/dossier"],
        "status": "met",
    },
    {
        "id": "P2",
        "source": "archivegpt",
        "demand": "Hallucination and OCR error are the observed failure modes; they must be caught.",
        "quote": "OCR errors and hallucinations limited perceived quality.",
        "how_this_system_answers": (
            "Every citation the compiler emits is re-opened with Parallel Extract and the "
            "quoted text must be found on the live page. A citation that fails is marked "
            "live_verified false and counts_toward_gate false, so a fabricated or drifted "
            "source cannot carry a threshold. On D04 this rejected ten citations and cost "
            "the identification -- the mechanism works against us as readily as for us."
        ),
        "evidence": [
            "app/partners/parallel_verify.py",
            "app/evidence_builder.py",
            "/v1/example/dossier",
        ],
        "status": "met",
    },
    {
        "id": "P3",
        "source": "archivegpt",
        "demand": "Trust depends on a transparent and explainable pipeline, not on model quality alone.",
        "quote": (
            "The successful integration of this approach depends not only on technical "
            "advancements, such as domain-specific fine-tuning, but even more on establishing "
            "trust among professionals, which could both be fostered through a transparent "
            "and explainable AI pipeline."
        ),
        "how_this_system_answers": (
            "The dossier is the product, not a by-product. Every response carries the seven "
            "thresholds with pass/fail, the claims with their sources, which sources survived "
            "the live audit, which Parallel surface produced what, and the elapsed time. "
            "/v1/stack names every sponsor surface with its call site and live status. The "
            "reasoning is inspectable without reading the code."
        ),
        "evidence": ["/v1/stack", "/v1/example/dossier", "/v1/dossiers"],
        "status": "met",
    },
    {
        "id": "P4",
        "source": "archivegpt",
        "demand": "Experts weighted preservation responsibility above technical performance.",
        "quote": (
            "Experts showed lower willingness to adopt AI tools, emphasizing concerns on "
            "preservation responsibility over technical performance."
        ),
        "how_this_system_answers": (
            "The scoring treats a confident wrong identification as the worst outcome and "
            "abstention as a correct one, and the published ablation leads with false-confident "
            "identifications rather than with accuracy. Repeated passes then found the system "
            "less stable than a single pass suggested, and one pass did put a wrong film "
            "forward as its leading candidate. That is published at /v1/eval/stability rather "
            "than corrected away, because preservation responsibility means reporting the pass "
            "that went badly, not the one that went well."
        ),
        "evidence": ["docs/ABLATION.md", "/v1/eval/stability", "app/gates/identity.py"],
        "status": "partially_met",
        "what_would_close_it": (
            "Enough repeated passes to state a false-confident rate with a confidence interval "
            "instead of a count, and a fix for the candidate slot accepting entities that are "
            "not films. Four passes over five fragments is a disclosure, not yet a rate."
        ),
    },
    {
        "id": "P5",
        "source": "archivegpt",
        "demand": "Human review is necessary in specialised domains; the model alone is not enough.",
        "quote": (
            "suggesting that human review is necessary to ensure the accuracy and quality of "
            "catalogue descriptions generated by the out-of-the-box model, particularly in "
            "specialized domains like archaeological cataloguing"
        ),
        "how_this_system_answers": (
            "No archivist has reviewed this system's output. That is stated on /v1/standards, "
            "in the README and in the dossier disclaimer, and it is why the gate withholds "
            "probable rather than shipping a verdict a reviewer never saw. The design assumes "
            "the reviewer; it has not yet met one."
        ),
        "evidence": ["/v1/standards", "docs/LIMITATIONS.md"],
        "status": "not_met",
        "what_would_close_it": (
            "A moving-image archivist running the five development fragments and recording "
            "where the dossiers helped and where they wasted their time. Roughly a day of "
            "one professional's attention. Nothing in the code substitutes for it."
        ),
    },
    {
        "id": "P6",
        "source": "archivegpt",
        "demand": "Domain-specific fine-tuning is named as one of the technical advancements needed.",
        "quote": "depends not only on technical advancements, such as domain-specific fine-tuning",
        "how_this_system_answers": (
            "No fine-tuning was done. This runs stock Gemini 2.5 Flash. The domain knowledge "
            "lives in the workflow -- verbatim transcription, rare-string search, an archival "
            "source policy, a falsification pass -- rather than in the weights. Whether that "
            "substitutes for fine-tuning is untested here."
        ),
        "evidence": ["app/adk_app.py"],
        "status": "not_met",
        "what_would_close_it": (
            "A fine-tune on catalogued archival stills and intertitles, measured against this "
            "same corpus. Out of scope for a hackathon and not attempted."
        ),
    },
    {
        "id": "P7",
        "source": "fiaf",
        "demand": "Information in a record must be derived from a source.",
        "quote": "Information entered in a record must be derived from a source.",
        "how_this_system_answers": (
            "A claim with an empty source list is reported but cannot pass a threshold. The "
            "control arm produced seven identifications with no citable source; the full "
            "system produced none."
        ),
        "evidence": ["/v1/standards", "app/standards.py", "docs/ABLATION.md"],
        "status": "met",
    },
    {
        "id": "P8",
        "source": "fiaf",
        "demand": "Where an attribution is uncertain, name the possibilities and qualify the uncertainty.",
        "quote": (
            "if the Agent could be one of two or more possibilities then name them and qualify "
            "that there is uncertainty as to which is correct"
        ),
        "how_this_system_answers": (
            "candidates is a first-class verdict carrying every surviving candidate with its "
            "own evidence and score, not a single answer with a confidence number attached."
        ),
        "evidence": ["/v1/example/dossier", "app/gates/identity.py"],
        "status": "met",
    },
    {
        "id": "P9",
        "source": "mostly_lost_blog",
        "demand": (
            "The professional method is clue-calling against searchable databases -- read what "
            "is on the screen, then go and look it up."
        ),
        "quote": (
            "As films roll, they shout out clues they see onscreen that might help identify the "
            "film and search online databases for titles that match the clues."
        ),
        "how_this_system_answers": (
            "That is the pipeline, in order. VisualExaminer transcribes what is on screen "
            "verbatim without guessing; PhraseHunter takes the highest-discrimination strings "
            "and searches them as quoted literals. The system automates the documented method "
            "rather than inventing one."
        ),
        "evidence": ["app/adk_app.py", "app/partners/parallel_research.py"],
        "status": "met",
    },
    {
        "id": "P10",
        "source": "mostly_lost_2019",
        "demand": (
            "Identification is hard for experts working together: the published hit rate is "
            "23-30 percent per workshop, on films screened precisely because they are difficult."
        ),
        "quote": (
            "Of the 187 unidentified titles screened at the workshop in 2018, 56 films - 30 "
            "percent - were identified during the event."
        ),
        "how_this_system_answers": (
            "This sets the difficulty of the task, not a score to beat. The two corpora are "
            "not comparable -- theirs is 187 genuinely hard films, ours is five with a sealed "
            "answer key -- and no claim of superiority is made or supportable at n=5. It is "
            "cited because a reader deserves to know that the humans who do this for a living "
            "identify well under half of what they screen."
        ),
        "evidence": ["docs/IMPACT.md", "/v1/eval/arm-c"],
        "status": "met",
    },
    {
        "id": "P11",
        "source": "mostly_lost_2019",
        "demand": (
            "The corpus includes films that are already catalogued under the wrong title, not "
            "merely films with no title at all."
        ),
        "quote": "unidentified, under-identified or misidentified silent and early sound films",
        "how_this_system_answers": (
            "contradict is a required outcome in the corpus and a first-class verdict. D05 "
            "arrives labelled 'Those who pay'; the system surfaced 'Through the Breakers' "
            "(1909) with a cited contradiction rather than accepting the supplied label."
        ),
        "evidence": ["/v1/presets", "/v1/eval/arm-c"],
        "status": "met",
    },
    {
        "id": "P13",
        "source": "heuer_ach",
        "demand": (
            "Consider alternative hypotheses, and judge by inconsistent evidence rather than by "
            "supporting evidence."
        ),
        "quote": (
            "analysts must prioritize evidence diagnosticity rather than its availability or "
            "volume"
        ),
        "how_this_system_answers": (
            "This was a real failure before it was a feature. Nineteen recorded runs showed D04 "
            "producing exactly one candidate every time and then agreeing with it fourteen "
            "times, reaching five of seven thresholds on the wrong film in three of four runs. "
            "The gate now carries competing_hypotheses>=2, because a hypothesis nothing opposes "
            "cannot be discriminated against anything, and "
            "leading_hypothesis_least_contradicted, which is Heuer's inversion: prefer the "
            "hypothesis with the least inconsistent evidence, not the most supported one."
        ),
        "evidence": ["app/gates/identity.py", "/v1/eval/stability", "app/works.py"],
        "status": "met",
    },
    {
        "id": "P14",
        "source": "failing_to_falsify",
        "demand": (
            "Confirmation bias in an agent shows up in which evidence gets selected, not in how "
            "it is read, so a pipeline must be built to seek disconfirming evidence."
        ),
        "quote": (
            "confirmation bias manifests not in how evidence is interpreted, but in how evidence "
            "is selected"
        ),
        "how_this_system_answers": (
            "A dedicated Skeptic agent runs before the compiler and is now asked to find a "
            "rival identity that would explain the same clues, rather than only to attack the "
            "incumbent. Its contradictions are compiled as first-class claims, and a "
            "contradiction on the leading candidate fails a threshold. Whether that measurably "
            "reduces the bias on this corpus is reported at /v1/eval/stability rather than "
            "asserted here."
        ),
        "evidence": ["app/adk_app.py", "/v1/eval/stability"],
        "status": "partially_met",
        "what_would_close_it": (
            "A measured reduction in false-confident identifications across enough passes to "
            "state a rate. Roughly ten runs an era shows direction, not effect size."
        ),
    },
    {
        "id": "P12",
        "source": "pierce_2013",
        "demand": (
            "The loss is large, irreversible, and the surviving material is scattered across "
            "countries and formats."
        ),
        "quote": (
            "The loss of American silent-era feature films constitutes an alarming and "
            "irreversible loss to our nation's cultural record."
        ),
        "how_this_system_answers": (
            "Holdings research is deliberately international and the negative statement is "
            "constrained: the system may only say that no additional holding was found across "
            "the named catalogues it actually consulted, as of the search date. It is "
            "forbidden from writing 'lost', 'only surviving' or 'last copy' at all, because "
            "those are exactly the claims a census like this one exists to make and a language "
            "model is not entitled to."
        ),
        "evidence": ["app/adk_app.py", "app/gates/language.py"],
        "status": "met",
    },
]


def register() -> dict[str, Any]:
    """The register with its sources resolved and its own tally computed."""
    entries = []
    for item in REGISTER:
        entry = dict(item)
        entry["source"] = {"key": item["source"], **SOURCES[item["source"]]}
        entries.append(entry)

    tally: dict[str, int] = {"met": 0, "partially_met": 0, "not_met": 0}
    for entry in entries:
        tally[entry["status"]] += 1

    return {
        "entries": entries,
        "tally": tally,
        "total": len(entries),
        "disclaimer": (
            "No archivist has reviewed this project. These are demands made in published "
            "sources by people who have never seen it, quoted verbatim and answered here. "
            "Nobody cited endorses this system. Entries marked not_met are unanswered."
        ),
        "method": (
            "Sources were gathered using this project's own Parallel Search surface. Quotations "
            "are verbatim; where a source could not be retrieved directly it is not cited."
        ),
    }


def unmet() -> list[dict[str, Any]]:
    """The entries nothing in this system answers. Kept easy to find on purpose."""
    return [dict(item) for item in REGISTER if item["status"] != "met"]
