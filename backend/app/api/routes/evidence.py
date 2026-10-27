"""Evidence API routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_database
from app.api.schemas.evidence import (
    EvidenceDetailResponse,
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

    # Count matching records without loading them all.
    total = repository.count(source=source)

    # Fetch only the requested page.
    selected = repository.list_metadata(
        source=source,
        limit=limit,
        offset=offset,
    )

    settings = get_settings()

    evidence_ids = [
        str(row.id)
        for row in selected
    ]

    chunks = get_chunks_by_id(
        evidence_ids,
        chunk_store_dir=Path(
            settings.chunk_store_dir
        ),
    )

    items = []

    for row in selected:
        evidence_id = str(row.id)
        document = chunks.get(evidence_id)

        items.append(
            EvidenceDetailResponse(
                id=evidence_id,
                source=row.source,
                source_type=row.source_type,
                perspective=row.perspective,
                title=row.title,
                date=row.date,
                url=row.url,
                document_id=row.parent_document_id,
                chunk_index=row.chunk_index,
                text=(
                    document.text
                    if document
                    else ""
                ),
                metadata={},
                created_at=row.created_at,
            )
        )

    return EvidenceSearchResponse(
        items=tuple(items),
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

    return EvidenceSourcesResponse(
        items=tuple(
            EvidenceSourceResponse(
                source=source,
                count=count,
            )
            for source, count in repository.count_by_source()
        )
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

    metadata = repository.get_metadata_by_id(
        evidence_id
    )

    if metadata is None:
        raise HTTPException(
            status_code=404,
            detail="Evidence not found.",
        )

    settings = get_settings()

    chunks = get_chunks_by_id(
        [evidence_id],
        chunk_store_dir=Path(
            settings.chunk_store_dir
        ),
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
        document_id=metadata.parent_document_id,
        chunk_index=metadata.chunk_index,
        text=(
            document.text
            if document
            else ""
        ),
        metadata={},
        created_at=metadata.created_at,
    )