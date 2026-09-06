from datetime import datetime, timezone

from app.domain.enums import Perspective, SourceType
from app.domain.models.evidence import EvidenceDocument
from app.modules.preprocessing.pipeline import preprocess_documents


def make_document(
    *,
    document_id: str,
    text: str,
) -> EvidenceDocument:
    """Create a valid test evidence document."""

    return EvidenceDocument(
        id=f"{document_id}::chunk-0000",
        document_id=document_id,
        chunk_index=0,
        text=text,
        source="Test Source",
        source_type=SourceType.UCDP,
        perspective=Perspective.HISTORICAL,
        title="Test Document",
        date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        url="https://example.com/document",
        metadata={
            "category": "test",
        },
    )


def test_preprocess_documents_returns_chunks() -> None:
    """The pipeline should split a document into sequential chunks."""

    document = make_document(
        document_id="doc-001",
        text=(
            "This is the first sentence. "
            "This is the second sentence. "
            "This is the third sentence. "
            "This is the fourth sentence."
        ),
    )

    results = preprocess_documents(
        [document],
        chunk_size=50,
        chunk_overlap=20,
        near_duplicate_threshold=0.9,
        shingle_size=2,
    )

    assert len(results) > 1

    assert all(
        result.document_id == "doc-001"
        for result in results
    )

    assert [result.chunk_index for result in results] == list(
        range(len(results))
    )


def test_preprocess_documents_removes_exact_duplicates() -> None:
    """The pipeline should keep only the first exact duplicate."""

    text = (
        "The conflict began in the northern region. "
        "Negotiations continued throughout the year."
    )

    first_document = make_document(
        document_id="doc-001",
        text=text,
    )

    duplicate_document = make_document(
        document_id="doc-002",
        text=text,
    )

    results = preprocess_documents(
        [first_document, duplicate_document],
        chunk_size=500,
        chunk_overlap=50,
        near_duplicate_threshold=0.9,
        shingle_size=2,
    )

    assert len(results) == 1
    assert results[0].document_id == "doc-001"


def test_preprocess_documents_preserves_metadata() -> None:
    """The pipeline should preserve source metadata on processed chunks."""

    document = make_document(
        document_id="doc-001",
        text="This document contains enough content for preprocessing.",
    )

    results = preprocess_documents(
        [document],
        chunk_size=500,
        chunk_overlap=50,
        near_duplicate_threshold=0.9,
        shingle_size=2,
    )

    assert len(results) == 1

    result = results[0]

    assert result.document_id == "doc-001"
    assert result.chunk_index == 0
    assert result.source == "Test Source"
    assert result.source_type == SourceType.UCDP
    assert result.perspective == Perspective.HISTORICAL
    assert result.title == "Test Document"
    assert result.url == "https://example.com/document"
    assert result.metadata["category"] == "test"