"""API schemas for MIL-EVID analysis endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.analysis import (
    AnalysisEvidence,
    Citation,
    ClaimVerificationResult,
    ConfidenceResult,
    ContradictionResult,
    PerspectiveAnalysisResult,
)
from app.domain.models.query import QueryClassification


class AnalysisCreate(BaseModel):
    """Request body for starting a MIL-EVID analysis."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1)
    # retrieval_top_k: int = Field(default=15, ge=1, le=500)
    retrieval_top_k: int = Field(default=50, ge=1, le=500)
    rerank_top_k: int = Field(default=8, ge=1, le=100)
    acled_country: str | None = None
    acled_start_date: str | None = None
    acled_end_date: str | None = None
    acled_updated_since: str | None = None


class AnalysisResponse(BaseModel):
    """Complete response returned by the analysis endpoint."""

    model_config = ConfigDict(from_attributes=True)

    query: QueryClassification

    military_analysis: PerspectiveAnalysisResult
    legal_analysis: PerspectiveAnalysisResult
    historical_analysis: PerspectiveAnalysisResult

    evidence: tuple[AnalysisEvidence, ...] = ()

    contradictions: tuple[ContradictionResult, ...] = ()
    claim_verification: tuple[ClaimVerificationResult, ...] = ()

    confidence: ConfidenceResult
    citations: tuple[Citation, ...] = ()


class AnalysisStatusResponse(BaseModel):
    """Status response for an analysis."""

    analysis_id: str
    status: str


class PerspectiveAnalysisResponse(BaseModel):
    """Response containing one perspective analysis."""

    model_config = ConfigDict(from_attributes=True)

    perspective: PerspectiveAnalysisResult