"""SQLAlchemy ORM models.

Deliberate scope decision: this table stores evidence **metadata**
only — never full chunk text. Chunk text lives in the local JSONL
store (`repositories/chunk_file_store.py`) and is read directly by
retrieval index builders. This keeps the Postgres footprint small
(id/source/title/date/url ≈ a few hundred bytes/row) independent of
how much source text is ingested, which matters concretely for this
project: a free-tier 512MB database previously hit `DiskFull` storing
full text for ~285k UCDP records.

Uses SQLAlchemy 2.0's typed declarative style (`Mapped[...]`,
`mapped_column`) rather than the legacy `Column(...)` style, for
better static-typing support.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for MIL-EVID ORM models."""


class EvidenceMetadata(Base):
    """Metadata for one evidence chunk.

    Full chunk text is stored locally in JSONL.
    PostgreSQL stores only lightweight metadata.
    """

    __tablename__ = "evidence_metadata"

    id: Mapped[str] = mapped_column(
        String(512),
        primary_key=True,
    )

    source: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    perspective: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    title: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
    )

    url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )

    parent_document_id: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        index=True,
    )

    chunk_index: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_evidence_metadata_source_source_type",
            "source",
            "source_type",
        ),
    )