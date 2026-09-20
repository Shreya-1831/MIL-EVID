"""API schemas."""

from app.api.schemas.analysis import (
    AnalysisCreate,
    AnalysisResponse,
    AnalysisHistoryItem,
    AnalysisHistoryResponse,
    AnalysisDetailResponse,
    PersistedPerspectiveResponse,
    PersistedEvidenceResponse,
    PersistedClaimResponse,
    PersistedContradictionResponse,
)

from app.api.schemas.claim import (
    ClaimResponse,
    ClaimVerificationResponse,
)

from app.api.schemas.common import (
    ErrorResponse,
    PaginatedResponse,
)

from app.api.schemas.evidence import (
    EvidenceDetailResponse,
    EvidenceResponse,
    EvidenceSearchRequest,
    EvidenceSearchResponse,
    EvidenceSourceResponse,
    EvidenceSourcesResponse,
)

from app.api.schemas.ingestion import (
    IngestionDocument,
    IngestionRequest,
    IngestionResponse,
)

from app.api.schemas.retrieval import (
    RerankRequest,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    RetrievalStatusResponse,
)


__all__ = [
    # Analysis
    "AnalysisCreate",
    "AnalysisResponse",
    "AnalysisHistoryItem",
    "AnalysisHistoryResponse",
    "AnalysisDetailResponse",
    "PersistedPerspectiveResponse",
    "PersistedEvidenceResponse",
    "PersistedClaimResponse",
    "PersistedContradictionResponse",

    # Claims
    "ClaimResponse",
    "ClaimVerificationResponse",

    # Common
    "ErrorResponse",
    "PaginatedResponse",

    # Evidence
    "EvidenceDetailResponse",
    "EvidenceResponse",
    "EvidenceSearchRequest",
    "EvidenceSearchResponse",
    "EvidenceSourceResponse",
    "EvidenceSourcesResponse",

    # Ingestion
    "IngestionDocument",
    "IngestionRequest",
    "IngestionResponse",

    # Retrieval
    "RerankRequest",
    "RetrievalRequest",
    "RetrievalResponse",
    "RetrievalResult",
    "RetrievalStatusResponse",
]