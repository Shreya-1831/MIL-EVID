from __future__ import annotations

from datetime import datetime
from uuid import UUID

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


# ============================================================
# CREATE ANALYSIS
# ============================================================


class AnalysisCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        ...,
        min_length=1,
    )

    retrieval_top_k: int = Field(
        default=50,
        ge=1,
        le=500,
    )

    rerank_top_k: int = Field(
        default=8,
        ge=1,
        le=100,
    )

    acled_country: str | None = None
    acled_start_date: str | None = None
    acled_end_date: str | None = None
    acled_updated_since: str | None = None


# ============================================================
# ANALYSIS RESPONSE
# ============================================================


class AnalysisResponse(BaseModel):
    """
    Response returned when an analysis is created or completed.

    During processing, the analysis_id and status are available
    immediately while result fields remain None.

    Once the pipeline reaches "completed", all result fields
    are populated.
    """

    model_config = ConfigDict(
        from_attributes=True
    )

    analysis_id: UUID

    status: str

    query_text: str

    started_at: datetime | None = None

    completed_at: datetime | None = None

    # --------------------------------------------------------
    # Result fields
    #
    # Optional because POST /api/analysis returns immediately.
    # --------------------------------------------------------

    query: QueryClassification | None = None

    military_analysis: (
        PerspectiveAnalysisResult | None
    ) = None

    legal_analysis: (
        PerspectiveAnalysisResult | None
    ) = None

    historical_analysis: (
        PerspectiveAnalysisResult | None
    ) = None

    evidence: tuple[
        AnalysisEvidence, ...
    ] = ()

    contradictions: tuple[
        ContradictionResult, ...
    ] = ()

    claim_verification: tuple[
        ClaimVerificationResult, ...
    ] = ()

    confidence: ConfidenceResult | None = None

    citations: tuple[
        Citation, ...
    ] = ()


# ============================================================
# ANALYSIS HISTORY
# ============================================================


class AnalysisHistoryItem(BaseModel):
    """
    Lightweight representation used by the History page.
    """

    model_config = ConfigDict(
        from_attributes=True
    )

    analysis_id: UUID

    query_text: str

    status: str

    overall_confidence: float

    evidence_count: int

    started_at: datetime | None = None

    completed_at: datetime | None = None


class AnalysisHistoryResponse(BaseModel):
    analyses: list[AnalysisHistoryItem]


# ============================================================
# PERSISTED PERSPECTIVE
# ============================================================


class PersistedPerspectiveResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    perspective: str

    analysis_text: str


# ============================================================
# PERSISTED EVIDENCE
# ============================================================


class PersistedEvidenceResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID

    evidence_id: str

    source_name: str

    source_type: str

    title: str | None = None

    evidence_text: str

    source_url: str | None = None

    publication_date: datetime | None = None

    perspective: str | None = None

    document_id: str | None = None

    chunk_index: int | None = None

    reranker_score: float | None = None

    original_rrf_score: float | None = None


# ============================================================
# PERSISTED CLAIM
# ============================================================


class PersistedClaimResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID

    claim_text: str

    perspective: str | None = None

    verdict: str

    support_score: float

    verified: bool


# ============================================================
# PERSISTED CONTRADICTION
# ============================================================


class PersistedContradictionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID

    evidence_a_id: str

    evidence_b_id: str

    status: str

    contradiction_type: str

    score: float

    explanation: str


# ============================================================
# ANALYSIS DETAIL
# ============================================================


class AnalysisDetailResponse(BaseModel):
    """
    Complete persisted representation used by AnalysisDetail.

    During processing, the persisted collections can still be
    empty because the pipeline has not reached the persistence
    stage yet.
    """

    model_config = ConfigDict(
        from_attributes=True
    )

    analysis_id: UUID

    query_text: str

    status: str

    final_answer: str

    overall_confidence: float

    started_at: datetime | None = None

    completed_at: datetime | None = None

    perspectives: list[
        PersistedPerspectiveResponse
    ] = []

    evidence: list[
        PersistedEvidenceResponse
    ] = []

    claims: list[
        PersistedClaimResponse
    ] = []

    contradictions: list[
        PersistedContradictionResponse
    ] = []