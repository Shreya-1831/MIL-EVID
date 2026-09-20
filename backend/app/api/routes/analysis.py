"""Analysis API routes for MIL-EVID."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_analysis_repository,
    get_analysis_service,
    get_current_user,
)
from app.api.schemas.analysis import (
    AnalysisCreate,
    AnalysisResponse,
)
from app.database.models import User
from app.repositories.analysis_repository import AnalysisRepository
from app.services.analysis_service import AnalysisService


router = APIRouter(
    prefix="/analysis",
    tags=["Analysis"],
)


# =========================================================
# CREATE ANALYSIS
# =========================================================

@router.post(
    "",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
)
def create_analysis(
    request: AnalysisCreate,
    service: AnalysisService = Depends(get_analysis_service),
    analysis_repository: AnalysisRepository = Depends(
        get_analysis_repository
    ),
    current_user: User = Depends(get_current_user),
) -> AnalysisResponse:

    result = service.analyze(
        user_id=current_user.id,
        query=request.query,
        analysis_repository=analysis_repository,
        retrieval_top_k=request.retrieval_top_k,
        rerank_top_k=request.rerank_top_k,
        acled_country=request.acled_country,
        acled_start_date=request.acled_start_date,
        acled_end_date=request.acled_end_date,
        acled_updated_since=request.acled_updated_since,
    )

    return AnalysisResponse.model_validate(result)


# =========================================================
# LIST ALL ANALYSES
# =========================================================

@router.get(
    "",
    status_code=status.HTTP_200_OK,
)
def list_analyses(
    analysis_repository: AnalysisRepository = Depends(
        get_analysis_repository
    ),
    current_user: User = Depends(get_current_user),
):
    """Return all analyses belonging to the current user."""

    return analysis_repository.list_analyses(
        user_id=current_user.id,
    )


# =========================================================
# GET ONE ANALYSIS
# =========================================================

@router.get(
    "/{analysis_id}",
    status_code=status.HTTP_200_OK,
)
def get_analysis(
    analysis_id: UUID,
    analysis_repository: AnalysisRepository = Depends(
        get_analysis_repository
    ),
    current_user: User = Depends(get_current_user),
):
    """Return one analysis belonging to the current user."""

    analysis = analysis_repository.get_analysis(
        analysis_id=analysis_id,
        user_id=current_user.id,
    )

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found.",
        )

    return analysis


# =========================================================
# DELETE ONE ANALYSIS
# =========================================================

@router.delete(
    "/{analysis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_analysis(
    analysis_id: UUID,
    analysis_repository: AnalysisRepository = Depends(
        get_analysis_repository
    ),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete one analysis belonging to the current user."""

    deleted = analysis_repository.delete_analysis(
        analysis_id=analysis_id,
        user_id=current_user.id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found.",
        )