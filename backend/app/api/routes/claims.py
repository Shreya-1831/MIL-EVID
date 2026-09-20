"""Claim API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas.claim import (
    ClaimResponse,
    ClaimVerificationResponse,
)

router = APIRouter(
    prefix="/claims",
    tags=["Claims"],
)


def _get_analysis_result(
    request: Request,
    analysis_id: str,
):
    """Retrieve an analysis result from the application analysis store."""

    analysis_store = getattr(
        request.app.state,
        "analysis_results",
        None,
    )

    if analysis_store is None:
        raise HTTPException(
            status_code=503,
            detail="Analysis result store is not initialized.",
        )

    result = analysis_store.get(analysis_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found.",
        )

    return result


def _get_claim(
    request: Request,
    analysis_id: str,
    claim_id: str,
):
    """Resolve a claim verification result from an analysis."""

    result = _get_analysis_result(
        request,
        analysis_id,
    )

    claim_results = result.claim_verification

    try:
        index = int(claim_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Claim ID must identify a claim within the analysis.",
        ) from None

    if index < 1 or index > len(claim_results):
        raise HTTPException(
            status_code=404,
            detail="Claim not found.",
        )

    return claim_results[index - 1]


@router.get(
    "/{analysis_id}/{claim_id}",
    response_model=ClaimResponse,
)
def get_claim(
    analysis_id: str,
    claim_id: str,
    request: Request,
) -> ClaimResponse:
    """Return a claim from a completed analysis."""

    claim = _get_claim(
        request,
        analysis_id,
        claim_id,
    )

    return ClaimResponse(
        id=claim_id,
        analysis_id=analysis_id,
        claim_text=claim.claim,
        perspective="",
        verdict=claim.status.value,
        confidence=float(claim.support_score),
    )


@router.get(
    "/{analysis_id}/{claim_id}/verification",
    response_model=ClaimVerificationResponse,
)
def get_claim_verification(
    analysis_id: str,
    claim_id: str,
    request: Request,
) -> ClaimVerificationResponse:
    """Return verification details for a claim."""

    claim = _get_claim(
        request,
        analysis_id,
        claim_id,
    )

    return ClaimVerificationResponse(
        claim_id=claim_id,
        verdict=claim.status.value,
        confidence=float(claim.support_score),
        evidence_ids=claim.supporting_evidence_ids,
    )


@router.get(
    "/{analysis_id}/{claim_id}/evidence",
)
def get_claim_evidence(
    analysis_id: str,
    claim_id: str,
    request: Request,
) -> list[str]:
    """Return evidence IDs supporting a claim."""

    claim = _get_claim(
        request,
        analysis_id,
        claim_id,
    )

    return list(claim.supporting_evidence_ids)