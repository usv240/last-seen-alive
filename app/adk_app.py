"""Five-role ADK workflow. Each output_key is separately inspectable in run state."""

from __future__ import annotations

import os

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.apps import App

from app.evidence_schema import CompiledEvidence
from app.partners.parallel_research import (
    census_named_catalogues,
    deep_holdings_research,
    search_archival_evidence,
)

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

visual_examiner = LlmAgent(
    name="VisualExaminer",
    model=MODEL,
    description="Extracts typed clues from an archival fragment without guessing its identity.",
    instruction="""
Inspect the supplied film fragment. Transcribe every legible intertitle VERBATIM, preserving
spelling and punctuation. Extract proper nouns, character names, logos, language, film-stock
edge marks, costume period, architecture, and possible performers. Return compact JSON only.
Do not identify the film and do not turn rare strings into a plot summary.
""",
    output_key="visual_clues",
)

phrase_hunter = LlmAgent(
    name="PhraseHunter",
    model=MODEL,
    description="Uses Parallel Search to find dated evidence for literal rare strings.",
    instruction="""
Read {visual_clues}. Select the highest-discrimination verbatim strings and proper nouns. Call
search_archival_evidence with two to five diverse queries, retaining quotation marks around exact
phrases. Return candidate identities and, for every factual claim, the URL and exact supporting
excerpt from the tool output. Never use model memory as a source.
""",
    tools=[search_archival_evidence],
    output_key="phrase_evidence",
)

holdings_researcher = LlmAgent(
    name="HoldingsResearcher",
    model=MODEL,
    description="Investigates alternate titles and surviving holdings across world catalogues.",
    instruction="""
Read {visual_clues} and {phrase_evidence}. For plausible candidates, call deep_holdings_research
to trace studio, performer, release date, alternate and foreign titles, restoration notices, and
named archive catalogues.

Then, for the single strongest candidate only, call census_named_catalogues. That commissions a
catalogue census which runs in the background and returns a handle, not results. Record that it was
commissioned and note its id; do not wait for it and do not describe coverage on its strength.

Describe coverage ONLY from catalogues deep_holdings_research actually consulted and cited. The
permitted negative formulation is: 'No additional holding was found across these named catalogues
as of this search date,' followed by those institution names.
Never write 'last copy', 'only surviving', 'sole', 'lost', or 'rediscovered'.
""",
    tools=[deep_holdings_research, census_named_catalogues],
    output_key="holdings_evidence",
)

skeptic = LlmAgent(
    name="Skeptic",
    model=MODEL,
    description="Attempts to disprove candidates using fresh Parallel searches.",
    instruction="""
Read {visual_clues}, {phrase_evidence}, and {holdings_evidence}. Actively try to disprove every
candidate: incompatible dates, wrong studio or country, performer career mismatch, reused stock
phrases, and competing attributions. Use search_archival_evidence for every web fact. Return a
JSON list of supported contradiction claims and unresolved questions. You do not issue a verdict.

Attacking the leading candidate is not enough. Search for a DIFFERENT film that
would explain the same clues: the same stock phrase in another studio's release,
the same performer in a neighbouring year, the same location in an unrelated
subject. Report any you find as a rival identity with its own sources.

This matters because the earlier agents hand you one hypothesis and everything
after them tends to accumulate agreement with it. A run that ends with one
candidate and a dozen supporting claims has not tested anything, and it is how
this system reached five of seven thresholds on a film that was simply wrong.
Your job is to give it something to be wrong against.
""",
    tools=[search_archival_evidence],
    output_key="skeptic_evidence",
)


# The four agents above research and write prose. The gate counts claims, not
# prose, so this fifth agent restates what they found in a typed shape. It has
# no tools on purpose: Gemini cannot combine controlled generation with function
# calling, and a compiler should not be able to go looking for new evidence
# while it is being asked to summarise the evidence already gathered.
#
# Nothing it emits is trusted on its own. app/evidence_builder.py checks every
# citation against what Parallel actually returned before the gate sees it.
evidence_compiler = LlmAgent(
    name="EvidenceCompiler",
    model=MODEL,
    description="Restates the investigation as typed claims and candidates for the deterministic gate.",
    instruction="""
Read {visual_clues}, {phrase_evidence}, {holdings_evidence}, and {skeptic_evidence}.

Emit the typed evidence structure. Rules:
- Copy URLs and excerpts EXACTLY as they appear in the research outputs. A URL you
  did not see in those outputs will be discarded and will weaken the candidate.
- Every claim needs at least one source. A claim you cannot cite must still be
  reported, with an empty source list, so a human can see what is unsupported.
- Include the Skeptic's contradictions as claims with stance "contradicts".
- score reflects the strength of cited evidence, not your confidence.
- Set temporal_compatibility and entity_compatibility to true only if you can
  point to cited claims that are mutually consistent. Default to false.
- Do not issue a verdict. Deterministic code and an archivist decide.

A candidate must NAME A FILM. A studio, a production company, an archive or
collection, a costume period, a subject heading, or a restatement like
"unidentified fragment" is not a candidate identity, and code will discard it.
If the strongest thing the evidence supports is a studio, say so in a claim and
leave the candidate list shorter.

List EVERY identity the evidence leaves open, not just the best one. Where the
research supports a second reading of the same clues, it belongs in candidates
with its own score and its own claims. A single candidate that nothing competes
with cannot be assessed: evidence only discriminates when there is something for
it to discriminate against, so an unopposed candidate will not pass the gate
however much support it has. Do not invent a filler rival to satisfy this — a
candidate with no cited claims helps nothing, and a wrong rival is worse than a
short list. If the evidence genuinely supports only one reading, submit one and
let the gate withhold.
""",
    output_schema=CompiledEvidence,
    output_key="compiled_evidence",
)

root_agent = SequentialAgent(
    name="LastSeenAliveWorkflow",
    description="Deterministic four-stage archival investigation; the identity gate runs after it.",
    sub_agents=[visual_examiner, phrase_hunter, holdings_researcher, skeptic, evidence_compiler],
)

app = App(root_agent=root_agent, name="last_seen_alive")
