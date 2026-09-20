"""Evidence ingestion API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import Perspective, SourceType


class IngestionDocument(BaseModel):
    """Document supplied for ingestion."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    source_type: SourceType
    perspective: Perspective | None = None
    title: str | None = None
    date: datetime | None = None
    url: str | None = None
    document_id: str | None = None
    chunk_index: int | None = Field(default=None, ge=0)


class IngestionRequest(BaseModel):
    """Evidence ingestion request."""

    model_config = ConfigDict(extra="forbid")

    documents: tuple[IngestionDocument, ...] = Field(
        ...,
        min_length=1,
    )


class IngestionResponse(BaseModel):
    """Evidence ingestion response."""

    status: str
    documents_received: int
    documents_processed: int
    exact_duplicates: int
    near_duplicates: int