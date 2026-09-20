"""Claim API schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ClaimResponse(BaseModel):
    """Claim verification information."""

    model_config = ConfigDict(extra="forbid")

    id: str
    analysis_id: str
    claim_text: str
    verdict: str
    confidence: float = Field(ge=0.0, le=1.0)
    verified: bool
    evidence_ids: tuple[str, ...] = ()


class ClaimVerificationResponse(BaseModel):
    """Claim verification result."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str
    verdict: str
    confidence: float = Field(ge=0.0, le=1.0)
    verified: bool
    evidence_ids: tuple[str, ...] = ()