from app.domain.enums import SourceType
from app.domain.models.evidence import EvidenceDocument
from app.modules.preprocessing.chunker import (
    chunk_document,
    generate_chunk_id,
)


def test_generate_chunk_id() -> None:
    chunk_id = generate_chunk_id(
        "source-001",
        0,
    )

    assert chunk_id == "source-001::chunk-0000"


def test_chunk_document_preserves_document_id() -> None:
    document = EvidenceDocument(
        id="source-001",
        document_id="source-001",
        chunk_index=0,
        text=(
            "The first sentence contains important evidence. "
            "The second sentence provides additional context. "
            "The third sentence contains further information."
        ),
        source="UCDP",
        source_type=SourceType.UCDP,
    )

    chunks = chunk_document(
        document,
        chunk_size=80,
        chunk_overlap=20,
    )

    assert len(chunks) > 1

    for index, chunk in enumerate(chunks):
        assert chunk.document_id == "source-001"
        assert chunk.chunk_index == index
        assert chunk.id == generate_chunk_id(
            "source-001",
            index,
        )


def test_chunk_document_preserves_metadata() -> None:
    document = EvidenceDocument(
        id="source-002",
        document_id="source-002",
        chunk_index=0,
        text=(
            "Sentence one contains evidence. "
            "Sentence two contains additional evidence."
        ),
        source="UCDP",
        source_type=SourceType.UCDP,
        metadata={
            "country": "Example Country",
        },
    )

    chunks = chunk_document(
        document,
        chunk_size=30,
        chunk_overlap=10,
    )

    assert chunks

    for chunk in chunks:
        assert (
            chunk.metadata["country"]
            == "Example Country"
        )
        assert (
            chunk.metadata["chunk_count"]
            == len(chunks)
        )