"""Evidence ingestion API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas.ingestion import (
    IngestionRequest,
    IngestionResponse,
)
from app.domain.models.evidence import EvidenceDocument

router = APIRouter(
    prefix="/ingestion",
    tags=["Ingestion"],
)


@router.post(
    "",
    response_model=IngestionResponse,
)
def ingest_evidence(
    request: IngestionRequest,
    http_request: Request,
) -> IngestionResponse:
    service = getattr(
        http_request.app.state,
        "evidence_ingestion_service",
        None,
    )

    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Evidence ingestion service is not initialized.",
        )

    documents = tuple(
        EvidenceDocument(
            id=document.id,
            source=document.source,
            source_type=document.source_type,
            perspective=document.perspective,
            title=document.title,
            date=document.date,
            url=document.url,
            text=document.text,
            document_id=document.document_id
        )
        for document in request.documents
    )

    processed = service.ingest(documents)

    return IngestionResponse(
        status="completed",
        documents_received=len(documents),
        documents_processed=len(processed),
        exact_duplicates=service.indexed_exact_documents,
        near_duplicates=service.indexed_near_documents,
    )


@router.get("")
def ingestion_status(
    request: Request,
) -> dict[str, int | str]:
    service = getattr(
        request.app.state,
        "evidence_ingestion_service",
        None,
    )

    if service is None:
        return {
            "status": "unavailable",
            "indexed_exact_documents": 0,
            "indexed_near_documents": 0,
        }

    return {
        "status": "available",
        "indexed_exact_documents": service.indexed_exact_documents,
        "indexed_near_documents": service.indexed_near_documents,
    }