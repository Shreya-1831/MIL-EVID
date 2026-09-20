"""Analysis API routes for MIL-EVID."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.api.dependencies import (
    get_analysis_repository,
    get_analysis_service,
    get_current_user,
)
from app.api.schemas.analysis import (
    AnalysisCreate,
    AnalysisResponse,
    AnalysisHistoryResponse,
    AnalysisHistoryItem,
    AnalysisDetailResponse,
    PersistedClaimResponse,
    PersistedContradictionResponse,
    PersistedEvidenceResponse,
    PersistedPerspectiveResponse,
)
from app.database.session import get_session_factory
from app.database.models import User
from app.repositories.analysis_repository import (
    AnalysisRepository,
)
from app.services.analysis_service import (
    AnalysisService,
)


router = APIRouter(
    prefix="/analysis",
    tags=["Analysis"],
)


# ============================================================
# BACKGROUND EXECUTOR
# ============================================================

_analysis_executor = ThreadPoolExecutor(
    max_workers=4,
    thread_name_prefix="mil-evid-analysis",
)


# ============================================================
# BACKGROUND ANALYSIS WORKER
# ============================================================


def _run_analysis_background(
    *,
    service: AnalysisService,
    user_id: UUID,
    analysis_id: UUID,
    query: str,
    retrieval_top_k: int,
    rerank_top_k: int,
    acled_country: str | None,
    acled_start_date: str | None,
    acled_end_date: str | None,
    acled_updated_since: str | None,
) -> None:
    """
    Run the expensive analysis in a background thread.

    A completely new SQLAlchemy session is created here.
    We intentionally do NOT reuse the request-scoped session.
    """

    db = get_session_factory()()

    try:
        analysis_repository = AnalysisRepository(db)

        service.analyze(
            user_id=user_id,
            query=query,
            analysis_repository=analysis_repository,
            analysis_id=analysis_id,
            retrieval_top_k=retrieval_top_k,
            rerank_top_k=rerank_top_k,
            acled_country=acled_country,
            acled_start_date=acled_start_date,
            acled_end_date=acled_end_date,
            acled_updated_since=acled_updated_since,
        )

    except Exception:
        # The service already marks the analysis as failed.
        # We log here so the background thread does not silently
        # swallow the exception.
        import logging

        logging.getLogger("mil_evid").exception(
            "Background analysis failed: %s",
            analysis_id,
        )

    finally:
        db.close()


# ============================================================
# CREATE ANALYSIS
# ============================================================


@router.post(
    "",
    response_model=AnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_analysis(
    request: AnalysisCreate,
    service: AnalysisService = Depends(
        get_analysis_service
    ),
    analysis_repository: AnalysisRepository = Depends(
        get_analysis_repository
    ),
    current_user: User = Depends(
        get_current_user
    ),
) -> AnalysisResponse:
    """
    Create an analysis and start it in the background.

    The API returns immediately with the analysis ID.
    The frontend can then poll GET /api/analysis/{id}
    to observe the real backend pipeline status.
    """

    # --------------------------------------------------------
    # Create processing record immediately
    # --------------------------------------------------------

    from datetime import datetime, timezone

    started_at = datetime.now(timezone.utc)

    analysis_record = (
        analysis_repository.create_processing_analysis(
            user_id=current_user.id,
            query_text=request.query,
            started_at=started_at,
        )
    )

    analysis_id = analysis_record.id

    # --------------------------------------------------------
    # Start background analysis
    # --------------------------------------------------------

    _analysis_executor.submit(
        _run_analysis_background,
        service=service,
        user_id=current_user.id,
        analysis_id=analysis_id,
        query=request.query,
        retrieval_top_k=request.retrieval_top_k,
        rerank_top_k=request.rerank_top_k,
        acled_country=request.acled_country,
        acled_start_date=request.acled_start_date,
        acled_end_date=request.acled_end_date,
        acled_updated_since=request.acled_updated_since,
    )

    # --------------------------------------------------------
    # Return immediately
    # --------------------------------------------------------

    return AnalysisResponse(
        analysis_id=analysis_id,
        status=analysis_record.status,
        query_text=request.query,
        started_at=analysis_record.started_at,
        completed_at=None,
        query=None,
        military_analysis=None,
        legal_analysis=None,
        historical_analysis=None,
        evidence=[],
        contradictions=[],
        claim_verification=[],
        confidence=None,
        citations=[],
    )


# ============================================================
# LIST ALL ANALYSES
# ============================================================


@router.get(
    "",
    response_model=AnalysisHistoryResponse,
    status_code=status.HTTP_200_OK,
)
def list_analyses(
    analysis_repository: AnalysisRepository = Depends(
        get_analysis_repository
    ),
    current_user: User = Depends(
        get_current_user
    ),
) -> AnalysisHistoryResponse:

    rows = analysis_repository.list_analyses(
        user_id=current_user.id
    )

    analyses = [
        AnalysisHistoryItem(
            analysis_id=analysis.id,
            query_text=query.query_text,
            status=analysis.status,
            overall_confidence=float(
                analysis.overall_confidence
            ),
            evidence_count=evidence_count,
            started_at=analysis.started_at,
            completed_at=analysis.completed_at,
        )
        for analysis, query, evidence_count in rows
    ]

    return AnalysisHistoryResponse(
        analyses=analyses
    )


# ============================================================
# GET ONE ANALYSIS
# ============================================================


@router.get(
    "/{analysis_id}",
    response_model=AnalysisDetailResponse,
    status_code=status.HTTP_200_OK,
)
def get_analysis(
    analysis_id: UUID,
    analysis_repository: AnalysisRepository = Depends(
        get_analysis_repository
    ),
    current_user: User = Depends(
        get_current_user
    ),
) -> AnalysisDetailResponse:

    analysis = analysis_repository.get_analysis(
        analysis_id=analysis_id,
        user_id=current_user.id,
    )

    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found.",
        )

    query = analysis_repository.get_query_for_analysis(
        analysis_id=analysis_id,
        user_id=current_user.id,
    )

    if query is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis query not found.",
        )

    perspectives = (
        analysis_repository.get_perspectives(
            analysis_id
        )
    )

    evidence = (
        analysis_repository.get_evidence(
            analysis_id
        )
    )

    claims = (
        analysis_repository.get_claims(
            analysis_id
        )
    )

    contradictions = (
        analysis_repository.get_contradictions(
            analysis_id
        )
    )

    return AnalysisDetailResponse(
        analysis_id=analysis.id,
        query_text=query.query_text,
        status=analysis.status,
        final_answer=analysis.final_answer,
        overall_confidence=float(
            analysis.overall_confidence
        ),
        started_at=analysis.started_at,
        completed_at=analysis.completed_at,
        perspectives=[
            PersistedPerspectiveResponse.model_validate(
                row
            )
            for row in perspectives
        ],
        evidence=[
            PersistedEvidenceResponse.model_validate(
                row
            )
            for row in evidence
        ],
        claims=[
            PersistedClaimResponse.model_validate(
                row
            )
            for row in claims
        ],
        contradictions=[
            PersistedContradictionResponse.model_validate(
                row
            )
            for row in contradictions
        ],
    )


# ============================================================
# DELETE ONE ANALYSIS
# ============================================================


@router.delete(
    "/{analysis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_analysis(
    analysis_id: UUID,
    analysis_repository: AnalysisRepository = Depends(
        get_analysis_repository
    ),
    current_user: User = Depends(
        get_current_user
    ),
) -> None:

    deleted = analysis_repository.delete_analysis(
        analysis_id=analysis_id,
        user_id=current_user.id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found.",
        )