"""
Evidence ingestion application service.

Coordinates preprocessing, local chunk storage, and
metadata persistence for large-scale evidence ingestion.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from app.domain.models.evidence import EvidenceDocument
from app.modules.preprocessing.pipeline import (
    IncrementalPreprocessingPipeline,
)
from app.repositories.chunk_file_store import append_unique_chunks
from app.repositories.evidence_repository import EvidenceRepository


class EvidenceIngestionService:
    """Application service for large-scale evidence ingestion."""

    def __init__(
        self,
        repository: EvidenceRepository,
        *,
        chunk_store_dir: str | Path,
        chunk_size: int,
        chunk_overlap: int,
        near_duplicate_threshold: float,
        shingle_size: int,
        enable_near_duplicates: bool = True,
    ) -> None:
        self._repository = repository
        self._chunk_store_dir = Path(chunk_store_dir)

        self._pipeline = IncrementalPreprocessingPipeline(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            near_duplicate_threshold=near_duplicate_threshold,
            shingle_size=shingle_size,
            enable_near_duplicates=enable_near_duplicates,
        )

    def ingest(
        self,
        documents: Sequence[EvidenceDocument],
    ) -> tuple[EvidenceDocument, ...]:
        """Preprocess and persist one batch.

        Flow:

        raw documents
            ↓
        cleaning
            ↓
        normalization
            ↓
        deduplication
            ↓
        chunking
            ↓
        local JSONL + PostgreSQL metadata

        The service processes batches incrementally so duplicate
        detection state survives across multiple CSV batches.
        """
        if not documents:
            return ()

        processed_documents = self._pipeline.process(documents)

        if not processed_documents:
            return ()

        # Group processed chunks by source.
        # Each source has its own JSONL file.
        documents_by_source: dict[
            str,
            list[EvidenceDocument],
        ] = {}

        for document in processed_documents:
            documents_by_source.setdefault(
                document.source,
                [],
            ).append(document)

        # Append this processed batch to the local source store.
        #
        # The ingestion runner feeds us multiple batches, so replacing
        # the JSONL file here would destroy previously processed data.
        for source_chunks in documents_by_source.values():
            append_unique_chunks(
                source_chunks,
                chunk_store_dir=self._chunk_store_dir,
            )

        # PostgreSQL stores metadata only.
        #
        # The actual evidence text is never passed to the repository.
        self._repository.bulk_upsert_evidence_metadata(
            processed_documents,
        )

        return tuple(processed_documents)

    @property
    def indexed_exact_documents(self) -> int:
        """Return the number of exact-content hashes indexed."""
        return self._pipeline.exact_duplicate_count

    @property
    def indexed_near_documents(self) -> int:
        """Return the number of documents indexed for near-duplicate detection."""
        return self._pipeline.near_duplicate_count