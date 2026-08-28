"""Typed shape the evidence compiler must emit.

The four research agents write prose. Prose cannot be gated: the deterministic
identity gate needs claims with subjects, stances, and sources it can count.
This schema is the contract between the model's reading of the investigation
and the code that decides.

The compiler is deliberately a separate agent with no tools. Gemini cannot use
controlled generation and function calling in the same request, and it should
not be able to run new searches while it is being asked to summarise what the
earlier searches found.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CompiledSource(BaseModel):
    url: str = Field(description="Exact URL as returned by Parallel. Never invent or shorten one.")
    excerpt: str = Field(
        description="Verbatim supporting text copied from that Parallel result.",
        max_length=1200,
    )


class CompiledClaim(BaseModel):
    claim_text: str = Field(description="One factual statement about a candidate identity.")
    subject: str = Field(description="The candidate_id this claim is about.")
    stance: Literal["supports", "contradicts", "neutral"]
    clue_family: Literal[
        "intertitle_text",
        "proper_noun",
        "performer",
        "studio_or_producer",
        "release_date",
        "alternate_title",
        "archive_holding",
        "visual_or_material",
    ] = Field(description="Which kind of evidence this is. Used to require independent families.")
    confidence_basis: str = Field(description="Why this claim is believed, in one sentence.")
    sources: list[CompiledSource] = Field(
        default_factory=list,
        description="Every source supporting this claim. A claim with no source cannot be decisive.",
    )


class CompiledCandidate(BaseModel):
    candidate_id: str = Field(description="Short stable slug, e.g. through_the_breakers_1928.")
    title: str
    year: str = Field(default="", description="Release year if evidenced, else empty.")
    score: float = Field(ge=0.0, le=1.0, description="Strength of the evidence, not model confidence.")
    rationale: str


class CompiledEvidence(BaseModel):
    """What the compiler returns. Code, not the model, turns this into a verdict."""

    candidates: list[CompiledCandidate] = Field(default_factory=list)
    claims: list[CompiledClaim] = Field(default_factory=list)
    temporal_compatibility: bool = Field(
        default=False,
        description="True only if every dated claim about the leading candidate is mutually consistent.",
    )
    entity_compatibility: bool = Field(
        default=False,
        description="True only if studio, performers and country are mutually consistent.",
    )
    unresolved_questions: list[str] = Field(default_factory=list)
