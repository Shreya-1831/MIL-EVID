"""Retrieval API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas.retrieval import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    RetrievalStatusResponse,
)
from app.domain.enums import Perspective

router = APIRouter(
    prefix="/retrieval",
    tags=["Retrieval"],
)


@router.post(
    "/search",
    response_model=RetrievalResponse,
)
def search_retrieval(
    request: RetrievalRequest,
    http_request: Request,
) -> RetrievalResponse:
    retriever = getattr(
        http_request.app.state,
        "perspective_retriever",
        None,
    )

    if retriever is None:
        raise HTTPException(
            status_code=503,
            detail="Retrieval service is not initialized.",
        )

    perspectives = (
        tuple(Perspective(value.lower()) for value in request.perspectives)
        if request.perspectives
        else (
            Perspective.MILITARY,
            Perspective.LEGAL,
            Perspective.HISTORICAL,
        )
    )

    results = retriever.search(
        request.query,
        perspectives,
        top_k=request.top_k,
    )

    return RetrievalResponse(
        query=request.query,
        results=tuple(
            RetrievalResult(
                chunk_id=result.chunk_id,
                score=float(result.score),
                ranks=dict(result.ranks),
            )
            for result in results
        ),
    )


@router.post(
    "/hybrid",
    response_model=RetrievalResponse,
)
def hybrid_retrieval(
    request: RetrievalRequest,
    http_request: Request,
) -> RetrievalResponse:
    retriever = getattr(
        http_request.app.state,
        "hybrid_retriever",
        None,
    )

    if retriever is None:
        raise HTTPException(
            status_code=503,
            detail="Hybrid retriever is not initialized.",
        )

    results = retriever.search(
        request.query,
        top_k=request.top_k,
    )

    return RetrievalResponse(
        query=request.query,
        results=tuple(
            RetrievalResult(
                chunk_id=result.chunk_id,
                score=float(result.score),
                ranks=dict(result.ranks),
            )
            for result in results
        ),
    )


@router.get(
    "/status",
    response_model=RetrievalStatusResponse,
)
def retrieval_status(
    request: Request,
) -> RetrievalStatusResponse:
    return RetrievalStatusResponse(
        status="available"
        if getattr(request.app.state, "hybrid_retriever", None)
        else "unavailable",
        bm25_available=getattr(
            request.app.state,
            "bm25_index",
            None,
        )
        is not None,
        faiss_available=getattr(
            request.app.state,
            "faiss_index",
            None,
        )
        is not None,
        reranker_available=getattr(
            request.app.state,
            "reranker",
            None,
        )
        is not None,
    )