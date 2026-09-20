"""Evidence API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import Perspective, SourceType


class EvidenceSearchRequest(BaseModel):
    """Request for evidence search."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1)
    perspective: Perspective | None = None
    source: str | None = None
    source_type: SourceType | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class EvidenceResponse(BaseModel):
    """Evidence metadata returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    source_type: SourceType
    perspective: Perspective | None = None
    title: str | None = None
    date: datetime | None = None
    url: str | None = None
    document_id: str | None = None
    chunk_index: int | None = None


class EvidenceDetailResponse(EvidenceResponse):
    """Evidence metadata and full evidence content."""

    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class EvidenceSearchResponse(BaseModel):
    """Evidence search response."""

    items: tuple[EvidenceDetailResponse, ...] = ()
    total: int
    limit: int
    offset: int


class EvidenceSourceResponse(BaseModel):
    """Evidence source with document count."""

    source: str
    count: int


class EvidenceSourcesResponse(BaseModel):
    """Available evidence sources."""

    items: tuple[EvidenceSourceResponse, ...] = ()