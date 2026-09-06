"""
Ingest ICRC and UN Peacemaker PDF sources.

Usage:

    python -m scripts.ingest_pdf_sources
    python -m scripts.ingest_pdf_sources --skip-db
    python -m scripts.ingest_pdf_sources --sources icrc
    python -m scripts.ingest_pdf_sources --sources un_peacemaker
Ingest ICRC and UN Peacemaker PDF sources.

Pipeline:

    PDF files
        ↓
    mapper
        ↓
    clean
        ↓
    normalize
        ↓
    exact deduplication
        ↓
    chunk
        ↓
    local JSONL (full text)
        +
    PostgreSQL (metadata only)

ICRC:
    Global IHL source. No country filtering.

UN Peacemaker:
    Filtered to the configured primary countries at mapper level.

Existing CSV chunks are preserved. PDF chunks are appended
idempotently using append_unique_chunks().
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import MilEvidError
from app.core.logging import configure_logging, get_logger
from app.database.session import get_session_factory
from app.domain.models.evidence import EvidenceDocument
from app.modules.ingestion.icrc_mapper import iter_icrc_documents
from app.modules.ingestion.un_peacemaker_mapper import (
    iter_un_peacemaker_documents,
)
from app.modules.preprocessing.chunker import chunk_document
from app.modules.preprocessing.cleaner import clean_evidence_document
from app.modules.preprocessing.country_filter import build_primary_country_set
from app.modules.preprocessing.deduplicator import remove_exact_duplicates
from app.modules.preprocessing.normalizer import normalize_evidence_document
from app.repositories.chunk_file_store import append_unique_chunks
from app.repositories.evidence_repository import EvidenceRepository

logger = get_logger(__name__)


def _process_source(
    source_label: str,
    raw_documents: list[EvidenceDocument],
    *,
    chunk_size: int,
    chunk_overlap: int,
    chunk_store_dir: Path,
) -> list[EvidenceDocument]:
    """Process and persist one PDF source."""

    if not raw_documents:
        logger.info(
            "no_documents_found",
            source=source_label,
        )
        return []

    # ---------------------------------------------------------
    # Clean
    # ---------------------------------------------------------
    cleaned = [
        clean_evidence_document(document)
        for document in raw_documents
    ]

    # ---------------------------------------------------------
    # Normalize
    # ---------------------------------------------------------
    normalized = [
        normalize_evidence_document(document)
        for document in cleaned
    ]

    # ---------------------------------------------------------
    # Exact deduplication
    # ---------------------------------------------------------
    deduped = remove_exact_duplicates(normalized)

    # ---------------------------------------------------------
    # Chunk
    # ---------------------------------------------------------
    all_chunks: list[EvidenceDocument] = []

    for document in deduped:
        all_chunks.extend(
            chunk_document(
                document,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        )

    logger.info(
        "source_processed",
        source=source_label,
        raw_documents=len(raw_documents),
        after_dedup=len(deduped),
        chunks=len(all_chunks),
    )

    # ---------------------------------------------------------
    # Local JSONL storage
    # ---------------------------------------------------------
    # A mapper should normally produce one source value, but
    # grouping keeps the store contract safe.
    by_source: dict[str, list[EvidenceDocument]] = {}

    for chunk in all_chunks:
        by_source.setdefault(
            chunk.source,
            [],
        ).append(chunk)

    for source_name, chunks in by_source.items():
        path, added = append_unique_chunks(
            chunks,
            chunk_store_dir=chunk_store_dir,
        )

        logger.info(
            "chunk_store_updated",
            source=source_name,
            path=str(path),
            processed=len(chunks),
            added=added,
            skipped=len(chunks) - added,
        )

    return all_chunks


def _upsert_metadata(
    chunks: list[EvidenceDocument],
) -> int:
    """Persist chunk metadata to PostgreSQL."""

    if not chunks:
        return 0

    session_factory = get_session_factory()

    with session_factory() as session:
        try:
            repository = EvidenceRepository(session)

            processed = repository.add_many(
                chunks,
                # batch_size=db_batch_size,
            )

            session.commit()

            logger.info(
                "db_metadata_upserted",
                count=processed,
            )

            return processed

        except MilEvidError as exc:
            session.rollback()

            logger.error(
                "db_metadata_upsert_failed",
                error=str(exc),
            )

            raise


def run(
    sources: set[str],
    skip_db: bool,
) -> None:
    """Run PDF ingestion for the requested sources."""

    settings = get_settings()
    configure_logging(settings.log_level)

    raw_data_dir = Path(settings.raw_data_dir)
    chunk_store_dir = Path(settings.chunk_store_dir)

    primary_country_set = build_primary_country_set(
        settings.primary_countries,
    )

    all_chunks: list[EvidenceDocument] = []

    # =========================================================
    # ICRC
    # =========================================================
    if "icrc" in sources:
        logger.info(
            "starting_source",
            source="icrc",
        )

        icrc_docs = list(
            iter_icrc_documents(
                raw_data_dir,
                # on_error="skip",
                on_error="raise",
            )
        )

        icrc_chunks = _process_source(
            "icrc",
            icrc_docs,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            chunk_store_dir=chunk_store_dir,
        )

        all_chunks.extend(icrc_chunks)

    # =========================================================
    # UN Peacemaker
    # =========================================================
    if "un_peacemaker" in sources:
        logger.info(
            "starting_source",
            source="un_peacemaker",
        )

        un_docs = list(
            iter_un_peacemaker_documents(
                raw_data_dir,
                primary_country_set=primary_country_set,
                # on_error="skip",
                on_error="raise",
            )
        )

        un_chunks = _process_source(
            "un_peacemaker",
            un_docs,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            chunk_store_dir=chunk_store_dir,
        )

        all_chunks.extend(un_chunks)

    # =========================================================
    # PostgreSQL metadata
    # =========================================================
    if skip_db:
        logger.info(
            "db_write_skipped",
            reason="--skip-db",
        )

    elif all_chunks:
        # _upsert_metadata(
        #     all_chunks,
        #     db_batch_size=settings.db_batch_size,
        # )
        _upsert_metadata(all_chunks)

    logger.info(
        "ingestion_complete",
        total_chunks=len(all_chunks),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
    )

    parser.add_argument(
        "--sources",
        nargs="+",
        choices=[
            "icrc",
            "un_peacemaker",
        ],
        default=[
            "icrc",
            "un_peacemaker",
        ],
        help="PDF sources to ingest. Default: both.",
    )

    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Write chunks locally without PostgreSQL metadata.",
    )

    args = parser.parse_args()

    run(
        sources=set(args.sources),
        skip_db=args.skip_db,
    )


if __name__ == "__main__":
    main()