"""SQLAlchemy ORM models for MIL-EVID persistence.

PostgreSQL stores application and analysis metadata/results.

Full retrieved evidence/chunk text remains available in the existing
local JSONL chunk store. Evidence records associated with an analysis
store the text that was actually used for that analysis so historical
analysis results remain explainable.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for MIL-EVID ORM models."""


class User(Base):
    """Authenticated MIL-EVID user."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    full_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )


class RefreshToken(Base):
    """Persisted refresh-token session metadata."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )


class Query(Base):
    """User-submitted analysis query."""

    __tablename__ = "queries"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    query_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    query_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "queries.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="completed",
        index=True,
    )

    final_answer: Mapped[str | None] = mapped_column(
        Text,
        nullable=False,
    )

    overall_confidence: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

class AnalysisPerspective(Base):
    """Perspective-specific analysis output."""

    __tablename__ = "analysis_perspectives"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    perspective: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    analysis_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "analysis_id",
            "perspective",
            name="uq_analysis_perspective",
        ),
    )


class AnalysisEvidence(Base):
    """Evidence snapshot used by a particular analysis."""

    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    evidence_id: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        index=True,
    )

    source_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    evidence_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    source_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    publication_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    perspective: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    relevance_score: Mapped[float | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
    )

    document_id: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    chunk_index: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    reranker_score: Mapped[float | None] = mapped_column(
        Numeric(8, 5),
        nullable=True,
    )

    original_rrf_score: Mapped[float | None] = mapped_column(
        Numeric(8, 5),
        nullable=True,
    )


class Claim(Base):
    """Generated claim and its verification result."""

    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    claim_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    perspective: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    verdict: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    support_score: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )

    verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )


class ClaimEvidence(Base):
    """Relationship between a claim and evidence used to verify it."""

    __tablename__ = "claim_evidence"

    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"),
        primary_key=True,
    )

    evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"),
        primary_key=True,
    )

    support_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    confidence: Mapped[float | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )


class AnalysisError(Base):
    """Error recorded during an analysis pipeline execution."""

    __tablename__ = "analysis_errors"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    error_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )


class EvidenceMetadata(Base):
    """Metadata for one evidence chunk.

    Full chunk text remains in the local JSONL chunk store.
    PostgreSQL stores lightweight global retrieval metadata.
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
    
class AnalysisContradiction(Base):
    """Contradiction detected between two evidence items."""

    __tablename__ = "analysis_contradictions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    evidence_a_id: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    evidence_b_id: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    contradiction_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    score: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )

    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )