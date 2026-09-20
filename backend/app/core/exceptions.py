"""Application-wide exception hierarchy.

Every exception the MIL-EVID codebase deliberately raises inherits
from `MilEvidError`. This lets the FastAPI exception handlers (wired
up in `app.main`) map domain errors to appropriate HTTP status codes
in one place, instead of each route doing its own try/except.

Modules should raise the most specific exception that applies rather
than a bare `Exception` or `ValueError`, so failures are diagnosable
and so the pipeline (`services/pipeline.py`) can distinguish
*critical* failures (which should abort the request) from
*non-critical* ones (which should degrade gracefully, e.g. dynamic
evidence being unavailable).
"""

from __future__ import annotations


class MilEvidError(Exception):
    """Base class for all deliberately-raised MIL-EVID errors."""

    status_code: int = 500
    error_code: str = "MIL_EVID_ERROR"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
    ) -> None:
        self.message = message

        if status_code is not None:
            self.status_code = status_code

        if error_code is not None:
            self.error_code = error_code

        super().__init__(message)


class ConfigurationError(MilEvidError):
    """Raised when required configuration is missing or invalid."""


# --- Query analysis ---


class QueryAnalysisError(MilEvidError):
    """Raised when a user query cannot be classified/understood."""


# --- Preprocessing ---


class PreprocessingError(MilEvidError):
    """Raised when text cleaning, chunking, or normalization fails."""


# --- Ingestion (raw source -> EvidenceDocument) ---


class IngestionError(MilEvidError):
    """Base class for failures turning a raw source file into evidence.

    Distinct from `PreprocessingError`, which operates on
    already-constructed `EvidenceDocument`s. Ingestion errors happen
    earlier: reading a CSV row or PDF and mapping it into the domain
    model in the first place.
    """


class CorruptSourceFileError(IngestionError):
    """Raised when a source file (PDF/CSV) cannot be parsed at all."""


class UnmappableRecordError(IngestionError):
    """Raised when a single raw record lacks fields required to build
    a valid `EvidenceDocument` (e.g. no text content). Callers should
    typically catch this per-record and skip, not abort the batch.
    """


# --- Retrieval ---


class RetrievalError(MilEvidError):
    """Base class for retrieval-stage failures."""


class IndexNotBuiltError(RetrievalError):
    """Raised when a retriever is queried before its index exists.

    Distinct from a generic `RetrievalError` because it points to a
    specific, actionable fix: run `scripts/build_indexes.py`.
    """


class IndexPersistenceError(RetrievalError):
    """Raised when saving or loading a BM25/FAISS index fails."""


# --- Dynamic evidence ---


class DynamicEvidenceError(MilEvidError):
    """Base class for dynamic (ACLED) evidence failures.

    Non-critical by design: the pipeline catches this and continues
    with static evidence only, rather than failing the whole request.
    """


class DynamicEvidenceUnavailableError(DynamicEvidenceError):
    """Raised when the external ACLED API cannot be reached or times out."""


class DynamicEvidenceValidationError(DynamicEvidenceError):
    """Raised when the ACLED API returns a response that fails validation."""


# --- Perspective analysis ---


class PerspectiveAnalysisError(MilEvidError):
    """Raised when a perspective analyzer fails to produce output."""


# --- Verification ---


class ContradictionDetectionError(MilEvidError):
    """Raised when contradiction detection fails for a comparison batch."""


class ClaimVerificationError(MilEvidError):
    """Raised when claim extraction or verification fails."""


# --- Confidence scoring ---


class ConfidenceScoringError(MilEvidError):
    """Raised when confidence scoring cannot be computed."""


# --- Pipeline orchestration ---


class PipelineError(MilEvidError):
    """Raised when a *critical* pipeline stage fails and the request
    cannot proceed (e.g. query analysis or hybrid retrieval)."""


# --- Persistence ---


class RepositoryError(MilEvidError):
    """Raised for database access failures in the repository layer."""

    status_code = 500
    error_code = "REPOSITORY_ERROR"