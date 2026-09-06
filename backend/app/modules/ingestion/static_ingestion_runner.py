"""Static dataset ingestion runners."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.ingestion.sipri_mapper import map_sipri_record
from app.modules.ingestion.static_ingestion import ingest_csv_file
from app.modules.ingestion.ucdp_dyadic_mapper import map_ucdp_dyadic_record
from app.modules.ingestion.ucdp_ged_mapper import map_ucdp_ged_record
from app.repositories.evidence_repository import EvidenceRepository
from app.services.evidence_ingestion_service import EvidenceIngestionService


CSV_BATCH_SIZE = 5000


def _create_ingestion_service(
    session: Session,
    *,
    enable_near_duplicates: bool = True,
) -> EvidenceIngestionService:
    """Create the ingestion service using application settings."""

    settings = get_settings()

    repository = EvidenceRepository(
        session,
        batch_size=settings.db_batch_size,
    )

    return EvidenceIngestionService(
        repository=repository,
        chunk_store_dir=settings.chunk_store_dir,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        near_duplicate_threshold=settings.near_duplicate_threshold,
        shingle_size=settings.shingle_size,
        enable_near_duplicates=enable_near_duplicates,
    )


def ingest_sipri_csv(
    *,
    csv_path: Path,
    session: Session,
) -> int:
    """Ingest a SIPRI CSV file."""

    ingestion_service = _create_ingestion_service(
        session,
        enable_near_duplicates=True,
    )

    documents = ingest_csv_file(
        csv_path=csv_path,
        mapper=map_sipri_record,
        ingestion_service=ingestion_service,
        batch_size=CSV_BATCH_SIZE,
    )

    return len(documents)


def ingest_ucdp_ged_csv(
    *,
    csv_path: Path,
    session: Session,
) -> int:
    """Ingest UCDP GED CSV data.

    Near-duplicate detection is disabled because GED records
    have stable source identifiers.
    """

    ingestion_service = _create_ingestion_service(
        session,
        enable_near_duplicates=False,
    )

    documents = ingest_csv_file(
        csv_path=csv_path,
        mapper=map_ucdp_ged_record,
        ingestion_service=ingestion_service,
        batch_size=CSV_BATCH_SIZE,
    )

    return len(documents)


def ingest_ucdp_dyadic_csv(
    *,
    csv_path: Path,
    session: Session,
) -> int:
    """Ingest UCDP Dyadic CSV data.

    Near-duplicate detection is disabled because Dyadic records
    have stable source identifiers.
    """

    ingestion_service = _create_ingestion_service(
        session,
        enable_near_duplicates=False,
    )

    documents = ingest_csv_file(
        csv_path=csv_path,
        mapper=map_ucdp_dyadic_record,
        ingestion_service=ingestion_service,
        batch_size=CSV_BATCH_SIZE,
    )

    return len(documents)