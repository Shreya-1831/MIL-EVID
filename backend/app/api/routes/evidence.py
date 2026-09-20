"""Evidence API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_database
from app.api.schemas.evidence import (
    EvidenceDetailResponse,
    EvidenceResponse,
    EvidenceSearchResponse,
    EvidenceSourceResponse,
    EvidenceSourcesResponse,
)
from app.core.config import get_settings
from app.repositories.chunk_file_store import get_chunks_by_id
from app.repositories.evidence_repository import EvidenceRepository

router = APIRouter(
    prefix="/evidence",
    tags=["Evidence"],
)


@router.get(
    "/{evidence_id}",
    response_model=EvidenceDetailResponse,
)
def get_evidence(
    evidence_id: str,
    db: Session = Depends(get_database),
) -> EvidenceDetailResponse:
    repository = EvidenceRepository(db)
    metadata = repository.get_metadata_by_id(evidence_id)

    if metadata is None:
        raise HTTPException(
            status_code=404,
            detail="Evidence not found.",
        )

    settings = get_settings()
    chunks = get_chunks_by_id(
        [evidence_id],
        settings.chunk_store_dir,
    )

    document = chunks.get(evidence_id)

    return EvidenceDetailResponse(
        id=str(metadata.id),
        source=metadata.source,
        source_type=metadata.source_type,
        perspective=metadata.perspective,
        title=metadata.title,
        date=metadata.date,
        url=metadata.url,
        parent_document_id=metadata.parent_document_id,
        chunk_index=metadata.chunk_index,
        evidence_text=document.text if document else None,
    )


@router.get(
    "",
    response_model=EvidenceSearchResponse,
)
def list_evidence(
    source: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_database),
) -> EvidenceSearchResponse:
    repository = EvidenceRepository(db)

    rows = repository.list_metadata()

    if source is not None:
        rows = tuple(row for row in rows if row.source == source)

    total = len(rows)
    selected = rows[offset : offset + limit]

    return EvidenceSearchResponse(
        items=tuple(
            EvidenceDetailResponse(
                id=str(row.id),
                source=row.source,
                source_type=row.source_type,
                perspective=row.perspective,
                title=row.title,
                date=row.date,
                url=row.url,
                parent_document_id=row.parent_document_id,
                chunk_index=row.chunk_index,
            )
            for row in selected
        ),
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/sources/list",
    response_model=EvidenceSourcesResponse,
)
def list_evidence_sources(
    db: Session = Depends(get_database),
) -> EvidenceSourcesResponse:
    repository = EvidenceRepository(db)
    rows = repository.list_metadata()

    counts: dict[str, int] = {}

    for row in rows:
        counts[row.source] = counts.get(row.source, 0) + 1

    return EvidenceSourcesResponse(
        items=tuple(
            EvidenceSourceResponse(
                source=source,
                count=count,
            )
            for source, count in sorted(counts.items())
        )
    )