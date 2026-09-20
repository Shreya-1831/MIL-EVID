"""Retrieval API schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RetrievalRequest(BaseModel):
    """Request for retrieval."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1)
    top_k: int = Field(default=20, ge=1, le=500)
    perspectives: tuple[str, ...] = ()


class RetrievalResult(BaseModel):
    """Single retrieval result."""

    chunk_id: str
    score: float
    ranks: dict[str, int] = Field(default_factory=dict)


class RetrievalResponse(BaseModel):
    """Retrieval response."""

    query: str
    results: tuple[RetrievalResult, ...] = ()


class RerankRequest(BaseModel):
    """Request for cross-encoder reranking."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1)
    chunk_ids: tuple[str, ...] = Field(..., min_length=1)
    top_k: int = Field(default=10, ge=1, le=100)


class RetrievalStatusResponse(BaseModel):
    """Retrieval subsystem status."""

    status: str
    bm25_available: bool
    faiss_available: bool
    reranker_available: bool