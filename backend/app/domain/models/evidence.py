"""Domain models representing evidence and retrieval results.

These are the core data structures that flow through nearly every
module in the pipeline: preprocessing produces `EvidenceDocument`
instances, retrieval wraps them in `RetrievedEvidence`, and
downstream analysis reads from both.

All models are immutable (`frozen=True`) by default. Preprocessing
and retrieval steps must build *new* instances rather than mutating
existing ones — this matches the "prefer pure functions, do not
mutate input objects" requirement and makes the pipeline's data flow
easy to reason about and test.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import Perspective, RetrievalMethod, SourceType

class EvidenceDocument(BaseModel):
    """A single unit of evidence, optionally representing a chunk."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        ...,
        min_length=1,
        description="Stable unique ID for this evidence/chunk.",
    )

    text: str = Field(..., min_length=1)

    source: str = Field(
        ...,
        description="Human-readable source name, e.g. 'UCDP'.",
    )

    source_type: SourceType

    perspective: Perspective | None = Field(
        default=None,
        description="Primary analytical perspective, if known.",
    )

    title: str | None = None

    date: datetime | None = Field(
        default=None,
        description="Publication or event date, if known.",
    )

    url: str | None = None

    # Identity of the original document before chunking.
    # For an unchunked document this can be None.
    document_id: str | None = None

    # Position of this chunk within its parent document.
    chunk_index: int | None = Field(
        default=None,
        ge=0,
    )

    metadata: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("text")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("EvidenceDocument.text must not be blank")
        return value