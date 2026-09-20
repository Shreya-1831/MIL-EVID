"""Perspective API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas.analysis import PerspectiveAnalysisResponse
from app.domain.enums import Perspective


router = APIRouter(
    prefix="/perspectives",
    tags=["Perspectives"],
)


@router.get("")
def list_perspectives() -> list[dict[str, str]]:
    """Return the analytical perspectives supported by MIL-EVID."""

    return [
        {
            "value": perspective.value,
            "name": perspective.name.lower(),
        }
        for perspective in Perspective
    ]


@router.get(
    "/{perspective}",
    response_model=PerspectiveAnalysisResponse,
)
def get_perspective(
    perspective: Perspective,
    request: Request,
) -> PerspectiveAnalysisResponse:
    """Return perspective-specific analysis configuration."""

    retriever = getattr(
        request.app.state,
        "perspective_retriever",
        None,
    )

    if retriever is None:
        raise HTTPException(
            status_code=503,
            detail="Perspective retrieval service is not initialized.",
        )

    return PerspectiveAnalysisResponse(
        perspective={
            "perspective": perspective,
            "analysis_text": "",
            "claims": (),
            "evidence_ids": (),
            "citations": (),
        }
    )