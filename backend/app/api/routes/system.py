"""System and administrative API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request

from app.repositories.chunk_file_store import count_chunks


router = APIRouter(
    prefix="/system",
    tags=["System"],
)


@router.get("/sources")
def system_sources(request: Request) -> dict:
    settings = request.app.state.settings

    chunk_counts = count_chunks(
        Path(settings.chunk_store_dir),
    )

    return {
        "sources": chunk_counts,
    }


@router.get("/indexes")
def system_indexes(request: Request) -> dict:
    retriever = getattr(
        request.app.state,
        "hybrid_retriever",
        None,
    )

    return {
        "bm25": {
            "available": retriever is not None
            and getattr(retriever, "_bm25_index", None) is not None,
        },
        "faiss": {
            "available": retriever is not None
            and getattr(retriever, "_faiss_index", None) is not None,
        },
        "reranker": {
            "available": getattr(
                request.app.state,
                "reranker",
                None,
            ) is not None,
        },
    }


@router.get("/configuration")
def system_configuration(request: Request) -> dict:
    settings = request.app.state.settings

    return {
        "environment": getattr(
            settings,
            "environment",
            None,
        ),
        "bm25_index_dir": settings.bm25_index_dir,
        "faiss_index_dir": settings.faiss_index_dir,
        "chunk_store_dir": str(settings.chunk_store_dir),
        "reranker_model": settings.reranker_model,
        "ollama_model": settings.ollama_model,
        "ollama_base_url": settings.ollama_base_url,
    }


@router.get("/status")
def system_status(request: Request) -> dict:
    started_at = request.app.state.started_at

    return {
        "status": "running",
        "started_at": started_at,
        "checked_at": datetime.now(timezone.utc),
    }