"""Domain models for analysis-stage output.

Covers evidence context, per-perspective analysis, contradiction
detection, claim verification, confidence scoring, and the final
assembled response returned by the API.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    ClaimVerificationStatus,
    ConfidenceLevel,
    ContradictionStatus,
    ContradictionType,
    Perspective,
    SourceType,
)
from app.domain.models.query import QueryClassification


class AnalysisEvidence(BaseModel):
    """Evidence item prepared for downstream analysis."""

    model_config = ConfigDict(frozen=True)

    evidence_id: str
    text: str

    source: str
    source_type: SourceType
    perspective: Perspective | None = None

    title: str | None = None
    date: datetime | None = None
    url: str | None = None

    document_id: str | None = None
    chunk_index: int | None = None

    reranker_score: float
    original_rrf_score: float
    ranks: tuple[int, ...]


class EvidenceContext(BaseModel):
    """Evidence context supplied to downstream LLM analysis."""

    model_config = ConfigDict(frozen=True)

    query: str

    evidence: tuple[AnalysisEvidence, ...] = Field(
        default_factory=tuple
    )

    direct_evidence_ids: tuple[str, ...] = Field(
        default_factory=tuple
    )

    contextual_evidence_ids: tuple[str, ...] = Field(
        default_factory=tuple
    )


class Citation(BaseModel):
    """A single citation linking analysis text back to source evidence."""

    model_config = ConfigDict(frozen=True)

    evidence_id: str
    source: str
    title: str | None = None
    url: str | None = None


class PerspectiveAnalysisResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    perspective: Perspective
    analysis_text: str
    claims: tuple[str, ...] = Field(default_factory=tuple)
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)
    citations: tuple[Citation, ...] = Field(default_factory=tuple)


class ContradictionResult(BaseModel):
    """Outcome of comparing two evidence items for consistency."""

    model_config = ConfigDict(frozen=True)

    evidence_a_id: str
    evidence_b_id: str
    status: ContradictionStatus
    contradiction_type: ContradictionType = ContradictionType.NONE
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model confidence in status.",
    )
    explanation: str


class ClaimVerificationResult(BaseModel):
    """Whether a single atomic claim is supported by retrieved evidence."""

    model_config = ConfigDict(frozen=True)

    claim: str
    supporting_evidence_ids: tuple[str, ...] = Field(
        default_factory=tuple
    )
    support_score: float = Field(..., ge=0.0, le=1.0)
    status: ClaimVerificationStatus
    verified: bool


class ConfidenceResult(BaseModel):
    """Explainable confidence score for the overall analysis.

    This is a system estimate of how well-grounded the response is
    given retrieved evidence — not an objective truth claim about
    the real-world situation. Consumers of the API should surface
    this distinction to end users.
    """

    model_config = ConfigDict(frozen=True)

    relevance_score: float = Field(..., ge=0.0, le=100.0)
    agreement_score: float = Field(..., ge=0.0, le=100.0)
    freshness_score: float = Field(..., ge=0.0, le=100.0)
    source_reliability_score: float = Field(..., ge=0.0, le=100.0)
    claim_support_score: float = Field(..., ge=0.0, le=100.0)

    final_score: float = Field(..., ge=0.0, le=100.0)
    confidence_level: ConfidenceLevel

    disclaimer: str = Field(
        default=(
            "This score is a system-generated estimate of evidence "
            "grounding, not a measure of real-world certainty."
        )
    )


class FinalAnalysisResponse(BaseModel):
    """The complete, structured output of the MIL-EVID pipeline."""
    model_config = ConfigDict(frozen=True)

    query: QueryClassification

    military_analysis: PerspectiveAnalysisResult
    legal_analysis: PerspectiveAnalysisResult
    historical_analysis: PerspectiveAnalysisResult

    # Final evidence used by the analysis pipeline
    evidence: tuple[AnalysisEvidence, ...] = Field(
        default_factory=tuple
    )

    contradictions: tuple[ContradictionResult, ...] = Field(
        default_factory=tuple
    )

    claim_verification: tuple[ClaimVerificationResult, ...] = Field(
        default_factory=tuple
    )

    confidence: ConfidenceResult

    citations: tuple[Citation, ...] = Field(
        default_factory=tuple
    )