"""MIL-EVID FastAPI application."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.database.session import init_db

from app.api.routes.auth import router as auth_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.claims import router as claims_router
from app.api.routes.evidence import router as evidence_router
from app.api.routes.health import router as health_router
from app.api.routes.ingestion import router as ingestion_router
from app.api.routes.perspectives import router as perspectives_router
from app.api.routes.retrieval import router as retrieval_router
from app.api.routes.system import router as system_router
from app.core.config import get_settings
from app.core.exceptions import MilEvidError
from app.modules.analysis.analyzer import EvidenceAnalyzer
from app.modules.analysis.claim_verifier import ClaimVerifier
from app.modules.analysis.confidence_scorer import ConfidenceScorer
from app.modules.analysis.context_builder import EvidenceContextBuilder
from app.modules.analysis.contradiction_detector import ContradictionDetector
from app.modules.analysis.evidence_guard import EvidenceConsistencyGuard
from app.modules.analysis.llm_client import OllamaClient
from app.modules.analysis.perspective_selector import (
    PerspectiveAwareCandidateSelector,
)
from app.modules.analysis.post_rerank_perspective_selector import (
    PostRerankPerspectiveSelector,
)
from app.modules.ingestion.acled_client import ACLEDClient
from app.modules.retrieval.acled_retriever import ACLEDDynamicRetriever
from app.modules.retrieval.hybrid_retriever import HybridRetriever
from app.modules.retrieval.perspective_query_builder import (
    PerspectiveQueryBuilder,
)
from app.modules.retrieval.perspective_retriever import (
    PerspectiveAwareRetriever,
)
from app.modules.retrieval.reranker import CrossEncoderReranker
from app.services.analysis_service import AnalysisService
# from app.services.evidence_ingestion_service import EvidenceIngestionService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize long-lived MIL-EVID resources."""

    settings = get_settings()
    init_db(settings)

    # ---------------------------------------------------------
    # 1. Retrieval indexes
    # ---------------------------------------------------------
    retriever = HybridRetriever.from_index_dirs(
        bm25_index_dir=Path(settings.bm25_index_dir),
        faiss_index_dir=Path(settings.faiss_index_dir),
        rrf_k=settings.rrf_k,
    )

    perspective_retriever = PerspectiveAwareRetriever(
        retriever=retriever,
        query_builder=PerspectiveQueryBuilder(),
    )

    # ---------------------------------------------------------
    # 2. Cross-encoder reranker
    # ---------------------------------------------------------
    reranker = CrossEncoderReranker(
        model_name=settings.reranker_model,
    )

    # ---------------------------------------------------------
    # 3. Evidence context + Ollama
    # ---------------------------------------------------------
    context_builder = EvidenceContextBuilder(
        chunk_store_dir=Path(settings.chunk_store_dir),
    )

    llm_client = OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
        num_predict=settings.ollama_num_predict,
        keep_alive=settings.ollama_keep_alive,
    )

    analyzer = EvidenceAnalyzer(
        llm_client=llm_client,
    )

    evidence_guard = EvidenceConsistencyGuard()

    contradiction_detector = ContradictionDetector(
        llm_client=llm_client,
    )

    claim_verifier = ClaimVerifier(
        llm_client=llm_client,
    )

    confidence_scorer = ConfidenceScorer()

    # ---------------------------------------------------------
    # 4. ACLED dynamic retrieval
    # ---------------------------------------------------------
    acled_retriever = None

    print(
        "ACLED configured:",
        settings.acled_configured,
    )

    if settings.acled_configured:
        acled_client = ACLEDClient(
            username=settings.acled_username,
            password=settings.acled_password,
        )

        acled_retriever = ACLEDDynamicRetriever(
            client=acled_client,
        )

    # ---------------------------------------------------------
    # 5. Existing AnalysisService
    # ---------------------------------------------------------
    service = AnalysisService(
        perspective_retriever=perspective_retriever,
        acled_retriever=acled_retriever,
        reranker=reranker,
        context_builder=context_builder,
        analyzer=analyzer,
        evidence_guard=evidence_guard,
        contradiction_detector=contradiction_detector,
        confidence_scorer=confidence_scorer,
        claim_verifier=claim_verifier,
        perspective_selector=PerspectiveAwareCandidateSelector(),
        post_rerank_perspective_selector=PostRerankPerspectiveSelector(),
        rerank_candidate_k=settings.rerank_candidate_k,
    )

    # ---------------------------------------------------------
    # 6. Evidence ingestion service
    # ---------------------------------------------------------
    # Uses the existing repository/session infrastructure.
    # The database session is request-scoped, so the ingestion
    # service itself must not retain a live Session.
    #
    # This is initialized only if the application provides the
    # required repository factory through the API dependency layer.
    # evidence_ingestion_service = None

    # ---------------------------------------------------------
    # 7. Store long-lived application resources
    # ---------------------------------------------------------
    app.state.analysis_service = service
    app.state.settings = settings
    app.state.started_at = datetime.now(timezone.utc)

    app.state.hybrid_retriever = retriever
    app.state.perspective_retriever = perspective_retriever
    app.state.reranker = reranker
    app.state.context_builder = context_builder
    app.state.llm_client = llm_client
    app.state.acled_retriever = acled_retriever
    # app.state.evidence_ingestion_service = evidence_ingestion_service

    yield

    # ---------------------------------------------------------
    # Shutdown
    # ---------------------------------------------------------
    app.state.analysis_service = None
    app.state.hybrid_retriever = None
    app.state.perspective_retriever = None
    app.state.reranker = None
    app.state.context_builder = None
    app.state.llm_client = None
    app.state.acled_retriever = None
    app.state.evidence_ingestion_service = None


def create_app() -> FastAPI:
    """Create the MIL-EVID FastAPI application."""

    app = FastAPI(
        title="MIL-EVID",
        description=(
            "Evidence-grounded multi-perspective military analysis API"
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.exception_handler(MilEvidError)
    async def mil_evid_error_handler(
        request: Request,
        exc: MilEvidError,
    ):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "detail": exc.message,
            },
        )

    # ---------------------------------------------------------
    # API routers
    # ---------------------------------------------------------
    app.include_router(health_router)
    app.include_router(auth_router, prefix="/api")
    app.include_router(analysis_router, prefix="/api")
    app.include_router(evidence_router, prefix="/api")
    app.include_router(retrieval_router, prefix="/api")
    app.include_router(claims_router, prefix="/api")
    app.include_router(perspectives_router, prefix="/api")
    app.include_router(ingestion_router, prefix="/api")
    app.include_router(system_router, prefix="/api")

    return app


app = create_app()