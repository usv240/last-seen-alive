# Conformance to archival cataloguing standards

Executable checks: [`tests/test_standards_conformance.py`](../tests/test_standards_conformance.py)

## Why this document exists, and what it is not

The strongest available evidence for a tool like this is an archivist using it
and telling you what is wrong. We do not have that, and this document does not
pretend to be a substitute. **No archivist has reviewed this system.**

What we could do instead is test conformance against the published standards
archivists actually work to, rather than against our own intuitions about what
an archivist would want. That is a weaker form of evidence than a practitioner
review, but it is a real one, and it is checkable: every requirement below is
quoted from a primary source with a page number, and every one has a test that
passes or fails against the system's actual output.

It also did what an external standard is supposed to do — **it found something
we had got wrong.** See R5.

### Sources

1. **The FIAF Moving Image Cataloguing Manual**, Linda Tadic (ed.), International
   Federation of Film Archives, 2016. Published free by FIAF; quotations below
   cite its printed page numbers.
   <https://www.fiafnet.org/pages/E-Resources/Cataloguing-Manual.html>
2. **EN 15907:2010**, *Film identification — Enhancing interoperability of
   metadata — Element sets and structures*, CEN. Element reference:
   <https://filmstandards.org/fsc/index.php/EN_15907>

---

## R1 — Every statement must derive from a source

> "Information entered in a record must be derived from a source."
> — FIAF Manual, §3 *Sources of Information*, p. 12

> "Cite the source(s) of information for the summary of the content of a
> Work/Variant." — FIAF Manual, p. 116

EN 15907 provides a dedicated **`Record Source`** element for the same purpose.

**Conformance: yes, and enforced rather than requested.** Every claim carries a
`sources` array; the citation registry discards any URL Parallel did not return
during that run, and `Claim.is_decisive_eligible` is false for a claim with no
surviving verified source. A claim with no source is *reported* rather than
hidden, so the archivist can see what is unsupported — which is the point of the
requirement.

**Tested by:** `test_r1_every_decisive_claim_carries_a_source`,
`test_r1_a_claim_without_a_source_cannot_carry_a_threshold`.

## R2 — Cite each source individually and consistently

> "Cite each individual source of information using an agreed upon,
> consistently applied citation style, such as The Chicago Manual of Style, or
> other style guide." — FIAF Manual, §3, p. 12

**Conformance: partial, and the divergence is deliberate.** We do not emit
Chicago style. Each source is a structured record — URL, hostname, verbatim
excerpt, retrieval provider, retrieval id, retrieval timestamp, and two
independent verification states — applied identically to every source. The
standard asks for "an agreed upon, consistently applied citation style"; ours is
machine-readable rather than prose, which is consistent but is not what a
cataloguer would paste into a record.

**Honest gap:** a system that produced Chicago-style citation strings alongside
the structured record would conform fully and would be more useful. It does not.

**Tested by:** `test_r2_every_source_has_the_same_structured_shape`.

## R3 — Begin with what the supplied source says; correct only on evidence

> "Begin with what the source of information says and correct it only when it is
> known to be ambiguous or erroneous." — FIAF Manual, p. 15

This is the rule that governs inherited catalogue metadata, and it cuts both
ways: do not discard a supplied title, and do not keep one that evidence
contradicts.

**Conformance: yes, and it is the reason the Tier E benchmark case exists.**
A `provided_label` is passed to the workflow, the Skeptic is directed to look for
evidence for and against it, and the required behaviour for D05 is `contradict` —
surface the conflict with evidence, never silently replace the label. The control
arm fails this rule: on one run it replaced the supplied title with an unrelated
third title and never mentioned the supplied one.

**Tested by:** `test_r3_a_supplied_label_reaches_the_workflow`,
`test_r3_the_benchmark_requires_contradiction_not_replacement`.

## R4 — When several identifications are possible, name them and qualify the uncertainty

> "if the Agent could be one of two or more possibilities then name them and
> qualify that there is uncertainty as to which is correct."
> — FIAF Manual, p. 147

**Conformance: yes.** This is exactly the `candidates` verdict: multiple named
candidates, each with its evidence score and its decisive claim ids, returned
together with the reason the probable-identity gate did not pass. The benchmark
requires this behaviour on two of ten cases and treats a single confident answer
there as a failure.

**Tested by:** `test_r4_candidates_verdict_names_all_of_them_with_the_uncertainty`.

## R5 — An unidentifiable entity still needs a supplied/devised title

> "Supplied/Devised titles are implemented for: […] moving image entities that
> are unidentifiable." — FIAF Manual, §A.2.5, p. 93

> "Partially or fully supplied/devised titles facilitate the discovery and
> identification of moving images without formal title. The title itself should
> be descriptive, describing the Work as succinctly as possible."
> — FIAF Manual, §A.2.5, p. 93

> "Where possible, use a Title + Title Type approach. This approach effectively
> removes the need for brackets by establishing the Title is supplied/devised by
> the cataloguer." — FIAF Manual, §A.2.5, p. 94

Recommended pattern (p. 94): *Who/what · What (activity) · Where · When ·
Who/what (source or collection)*, optionally with a form qualifier.

**Conformance: NO — this is what the exercise found, and it has now been fixed.**

An abstention previously returned no title at all. That is honest but unhelpful:
the archivist is left with a fragment they cannot file, search for, or refer to
in correspondence, which is the precise problem A.2.5 exists to solve. Being
unable to identify something is not a reason to leave it unnameable.

`app/devised_title.py` now returns a devised title on every `abstain` and
`candidates` verdict, built to the five-Ws pattern and carrying
`title_type: "supplied_devised"` per the Title + Title Type recommendation.

Two safeguards, because a devised title is a place an identification could be
smuggled in:

- It is **assembled by deterministic code from the typed clues**, never generated
  as prose. A model asked to devise a title reaches for a real film's title.
- It carries `is_identification: false` and `authority: "cataloguer_supplied"`,
  so no consumer can mistake it for a title the work bore.

**Tested by:** `test_r5_abstention_still_produces_a_filable_title`,
`test_r5_a_devised_title_is_marked_as_supplied_not_authoritative`,
`test_r5_a_devised_title_never_names_a_film`.

## R6 — Uncertainty must be explicit, not implied by omission

> "Optionally, when the role performed by an Agent is probable but not certain,
> provide the function name followed by a question mark." — FIAF Manual, p. 63

> "If the relationship is ambiguous, use a value to indicate this, for example,
> 'unknown'…" — FIAF Manual, p. 63

FIAF also recommends a distinguishing *precision* field specifying whether a
value is "exact, approximate or unknown" (§2.3.5.1–2.3.5.2, pp. 58–59).

**Conformance: yes, by a different mechanism.** We do not use question-mark
notation. Uncertainty is carried structurally: an explicit verdict enum
(`probable` / `candidates` / `abstain`), every one of the seven thresholds
returned with its boolean, and — importantly — a three-state citation audit where
`live_verified: null` means *not audited* and is distinguishable from `false`,
*audited and not found*. Omission never stands in for uncertainty.

**Tested by:** `test_r6_verdict_is_an_explicit_enum_never_an_absence`,
`test_r6_unaudited_is_distinguishable_from_audited_and_failed`.

## R7 — The entity model must separate work from carrier

EN 15907 defines *Cinematographic Work → Variant → Manifestation → Item*, and
FIAF adopts it. The distinction matters here because an identification is a claim
about a **Work**, while a fragment in hand is an **Item**.

**Conformance: partial, and stated plainly.** We reason about candidate Works and
about the Item we were handed, but we do not emit a four-level EN 15907 record,
and we do not model Variants or Manifestations at all. A fragment that is a
variant cut of a known work would be described as a candidate for the work, with
no way to say "this is the Italian release version". For a triage tool whose
output an archivist transcribes into their own system, that is a real limitation
rather than an oversight we have hidden.

**Tested by:** nothing — there is nothing to test. Recorded here so that the gap
is documented rather than discovered.

---

## Summary

| | Requirement | Source | Status |
|---|---|---|---|
| R1 | Every statement derives from a source | FIAF p. 12, 116; EN 15907 `Record Source` | **Conforms**, enforced in code |
| R2 | Cite each source individually and consistently | FIAF p. 12 | **Partial** — structured, not Chicago style |
| R3 | Begin with the supplied source; correct only on evidence | FIAF p. 15 | **Conforms** |
| R4 | Name multiple possibilities and qualify the uncertainty | FIAF p. 147 | **Conforms** |
| R5 | Unidentifiable entities still get a devised title | FIAF A.2.5, pp. 93–94 | **Was failing; now conforms** |
| R6 | Uncertainty explicit, never implied by omission | FIAF pp. 58–59, 63 | **Conforms**, different mechanism |
| R7 | Work / Variant / Manifestation / Item model | EN 15907 | **Partial** — no Variant or Manifestation modelling |

Five conform, two partially, and one was failing until this exercise ran.

## What this still does not tell us

Conformance to a cataloguing standard is not the same as being useful to a
cataloguer. These standards govern how a record should be *written*; they say
nothing about whether the evidence this system gathers is the evidence an
archivist would have wanted, whether the seven thresholds are set anywhere near
the right level, or whether a dossier is readable under time pressure. Those
questions need a practitioner, and they remain open.
