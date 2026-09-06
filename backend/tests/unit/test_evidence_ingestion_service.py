from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

from app.domain.enums import Perspective, SourceType
from app.domain.models.evidence import EvidenceDocument
from app.services.evidence_ingestion_service import EvidenceIngestionService


def make_document(
    *,
    document_id: str = "doc-001",
    text: str = (
        "This is the first sentence. "
        "This is the second sentence. "
        "This is the third sentence."
    ),
) -> EvidenceDocument:
    return EvidenceDocument(
        id=document_id,
        document_id=document_id,
        chunk_index=0,
        text=text,
        source="Test Source",
        source_type=SourceType.UCDP,
        perspective=Perspective.HISTORICAL,
        title="Test Evidence",
        date=datetime.now(timezone.utc),
        url="https://example.com",
        metadata={"test": True},
    )


def make_service(
    repository: Mock,
    chunk_store_dir: Path,
) -> EvidenceIngestionService:
    return EvidenceIngestionService(
        repository=repository,
        chunk_store_dir=chunk_store_dir,
        chunk_size=50,
        chunk_overlap=10,
        near_duplicate_threshold=0.9,
        shingle_size=2,
    )


def test_ingest_preprocesses_and_persists_documents(tmp_path: Path) -> None:
    repository = Mock()

    document = make_document()

    service = make_service(repository, tmp_path)

    results = service.ingest([document])

    repository.bulk_upsert_evidence_metadata.assert_called_once()

    persisted_documents = (
        repository.bulk_upsert_evidence_metadata.call_args.args[0]
    )

    assert len(results) > 0
    assert results == tuple(persisted_documents)

    assert all(chunk.document_id == "doc-001" for chunk in results)
    assert all(chunk.chunk_index is not None for chunk in results)

    store_files = list(tmp_path.glob("*.jsonl"))
    assert len(store_files) == 1


def test_ingest_returns_empty_tuple_for_empty_input(tmp_path: Path) -> None:
    repository = Mock()

    service = make_service(repository, tmp_path)

    results = service.ingest([])

    assert results == ()

    repository.bulk_upsert_evidence_metadata.assert_not_called()

    assert list(tmp_path.glob("*.jsonl")) == []


def test_ingest_does_not_mutate_input_document(tmp_path: Path) -> None:
    repository = Mock()

    document = make_document()

    original_text = document.text
    original_metadata = dict(document.metadata)
    original_id = document.id

    service = make_service(repository, tmp_path)

    service.ingest([document])

    assert document.text == original_text
    assert document.metadata == original_metadata
    assert document.id == original_id


def test_ingest_removes_exact_duplicates_before_persisting(
    tmp_path: Path,
) -> None:
    repository = Mock()

    service = make_service(repository, tmp_path)

    duplicate = make_document(
        document_id="doc-001",
        text="Same evidence text.",
    )

    duplicate_copy = duplicate.model_copy(
        update={
            "id": "doc-002",
            "document_id": "doc-002",
        }
    )

    results = service.ingest(
        [
            duplicate,
            duplicate_copy,
        ]
    )

    repository.bulk_upsert_evidence_metadata.assert_called_once()

    persisted_documents = (
        repository.bulk_upsert_evidence_metadata.call_args.args[0]
    )

    assert len(persisted_documents) > 0
    assert len(results) > 0

    # Exact duplicate content should be removed before chunking.
    assert len({chunk.text for chunk in results}) == len(results)

    # Only the surviving document should be represented.
    assert all(
        chunk.document_id == "doc-001"
        for chunk in results
    )