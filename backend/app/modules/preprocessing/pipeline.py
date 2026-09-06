"""Preprocessing pipeline orchestration."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.models.evidence import EvidenceDocument
from app.modules.preprocessing.chunker import chunk_documents
from app.modules.preprocessing.cleaner import clean_evidence_document
from app.modules.preprocessing.deduplicator import (
    compute_content_hash,
    remove_near_duplicates,
)
from app.modules.preprocessing.normalizer import normalize_evidence_document


def preprocess_documents(
    documents: Sequence[EvidenceDocument],
    *,
    chunk_size: int,
    chunk_overlap: int,
    near_duplicate_threshold: float,
    shingle_size: int,
) -> tuple[EvidenceDocument, ...]:
    """Run stateless preprocessing on a batch."""

    if not documents:
        return ()

    cleaned_documents = tuple(
        clean_evidence_document(document)
        for document in documents
    )

    normalized_documents = tuple(
        normalize_evidence_document(document)
        for document in cleaned_documents
    )

    exact_hashes: set[str] = set()
    exact_unique: list[EvidenceDocument] = []

    for document in normalized_documents:
        content_hash = compute_content_hash(document.text)

        if content_hash in exact_hashes:
            continue

        exact_hashes.add(content_hash)
        exact_unique.append(document)

    if not exact_unique:
        return ()

    near_unique = remove_near_duplicates(
        exact_unique,
        threshold=near_duplicate_threshold,
        shingle_size=shingle_size,
    )

    return chunk_documents(
        near_unique,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


class IncrementalPreprocessingPipeline:
    """Stateful preprocessing pipeline for large-scale ingestion."""

    def __init__(
        self,
        *,
        chunk_size: int,
        chunk_overlap: int,
        near_duplicate_threshold: float,
        shingle_size: int,
        enable_near_duplicates: bool = True,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError(
                "chunk_size must be greater than zero."
            )

        if chunk_overlap < 0:
            raise ValueError(
                "chunk_overlap must not be negative."
            )

        if chunk_overlap >= chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size."
            )

        if not 0 < near_duplicate_threshold <= 1:
            raise ValueError(
                "near_duplicate_threshold must be between 0 and 1."
            )

        if shingle_size <= 0:
            raise ValueError(
                "shingle_size must be greater than zero."
            )

        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._near_duplicate_threshold = near_duplicate_threshold
        self._shingle_size = shingle_size
        self._enable_near_duplicates = enable_near_duplicates

        # Persists across batches.
        self._exact_hashes: set[str] = set()

        # Only used when near-duplicate detection is enabled.
        self._near_duplicate_documents: list[EvidenceDocument] = []

    def process(
        self,
        documents: Sequence[EvidenceDocument],
    ) -> tuple[EvidenceDocument, ...]:
        """Process one ingestion batch."""

        if not documents:
            return ()

        # 1. Clean
        cleaned_documents = tuple(
            clean_evidence_document(document)
            for document in documents
        )

        # 2. Normalize
        normalized_documents = tuple(
            normalize_evidence_document(document)
            for document in cleaned_documents
        )

        # 3. Exact deduplication across batches
        exact_unique: list[EvidenceDocument] = []

        for document in normalized_documents:
            content_hash = compute_content_hash(document.text)

            if content_hash in self._exact_hashes:
                continue

            self._exact_hashes.add(content_hash)
            exact_unique.append(document)

        if not exact_unique:
            return ()

        # 4. Optional near-duplicate detection
        if self._enable_near_duplicates:
            combined_documents = (
                *self._near_duplicate_documents,
                *exact_unique,
            )

            deduplicated = remove_near_duplicates(
                combined_documents,
                threshold=self._near_duplicate_threshold,
                shingle_size=self._shingle_size,
            )

            existing_ids = {
                document.id
                for document in self._near_duplicate_documents
            }

            near_unique = tuple(
                document
                for document in deduplicated
                if document.id not in existing_ids
            )

            self._near_duplicate_documents.extend(near_unique)
        else:
            near_unique = tuple(exact_unique)

        if not near_unique:
            return ()

        # 5. Chunk
        return chunk_documents(
            near_unique,
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
        )

    @property
    def exact_duplicate_count(self) -> int:
        """Return the number of unique exact-content hashes seen."""
        return len(self._exact_hashes)

    @property
    def near_duplicate_count(self) -> int:
        """Return the number of documents retained for near-dedup state."""
        return len(self._near_duplicate_documents)