from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Sequence
from app.domain.enums import Perspective, SourceType
from app.domain.models.evidence import EvidenceDocument
from app.repositories.chunk_file_store import (
    append_unique_chunks,
    count_chunks,
    read_chunks,
    get_chunks_by_id,
)


def make_chunk(
    *,
    chunk_id: str,
    document_id: str = "doc-001",
    text: str = "Evidence text.",
) -> EvidenceDocument:
    return EvidenceDocument(
        id=chunk_id,
        document_id=document_id,
        chunk_index=0,
        text=text,
        source="Test Source",
        source_type=SourceType.UCDP,
        perspective=Perspective.HISTORICAL,
        title="Test Evidence",
        date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        url="https://example.com",
        metadata={"test": True},
    )


def test_append_unique_chunks_adds_new_chunks(
    tmp_path: Path,
) -> None:
    chunks = [
        make_chunk(chunk_id="doc-001::chunk-0000"),
        make_chunk(
            chunk_id="doc-001::chunk-0001",
            text="Second evidence text.",
        ),
    ]

    path, added = append_unique_chunks(
        chunks,
        chunk_store_dir=tmp_path,
    )

    assert path.exists()
    assert added == 2
    assert count_chunks(tmp_path)["test_source"] == 2


def test_append_unique_chunks_skips_existing_chunks(
    tmp_path: Path,
) -> None:
    chunks = [
        make_chunk(chunk_id="doc-001::chunk-0000"),
        make_chunk(
            chunk_id="doc-001::chunk-0001",
            text="Second evidence text.",
        ),
    ]

    append_unique_chunks(
        chunks,
        chunk_store_dir=tmp_path,
    )

    path, added = append_unique_chunks(
        chunks,
        chunk_store_dir=tmp_path,
    )

    assert path.exists()
    assert added == 0
    assert count_chunks(tmp_path)["test_source"] == 2


def test_append_unique_chunks_adds_only_new_chunks(
    tmp_path: Path,
) -> None:
    first_batch = [
        make_chunk(chunk_id="doc-001::chunk-0000"),
        make_chunk(
            chunk_id="doc-001::chunk-0001",
            text="Second evidence text.",
        ),
    ]

    second_batch = [
        make_chunk(chunk_id="doc-001::chunk-0001"),
        make_chunk(
            chunk_id="doc-001::chunk-0002",
            text="Third evidence text.",
        ),
    ]

    append_unique_chunks(
        first_batch,
        chunk_store_dir=tmp_path,
    )

    _, added = append_unique_chunks(
        second_batch,
        chunk_store_dir=tmp_path,
    )

    assert added == 1
    assert count_chunks(tmp_path)["test_source"] == 3


def test_append_unique_chunks_skips_duplicate_ids_within_batch(
    tmp_path: Path,
) -> None:
    chunks = [
        make_chunk(
            chunk_id="doc-001::chunk-0000",
            text="First version.",
        ),
        make_chunk(
            chunk_id="doc-001::chunk-0000",
            text="Duplicate version.",
        ),
    ]

    _, added = append_unique_chunks(
        chunks,
        chunk_store_dir=tmp_path,
    )

    assert added == 1
    assert count_chunks(tmp_path)["test_source"] == 1

    stored_chunks = list(
        read_chunks(tmp_path / "test_source.jsonl")
    )

    assert len(stored_chunks) == 1
    assert stored_chunks[0].text == "First version."

def test_get_chunks_by_id_returns_requested_chunks(
    tmp_path: Path,
) -> None:
    chunks = [
        make_chunk(
            chunk_id="doc-001::chunk-0000",
            text="First evidence text.",
        ),
        make_chunk(
            chunk_id="doc-001::chunk-0001",
            text="Second evidence text.",
        ),
        make_chunk(
            chunk_id="doc-001::chunk-0002",
            text="Third evidence text.",
        ),
    ]

    append_unique_chunks(
        chunks,
        chunk_store_dir=tmp_path,
    )

    result = get_chunks_by_id(
        [
            "doc-001::chunk-0000",
            "doc-001::chunk-0002",
        ],
        chunk_store_dir=tmp_path,
    )

    assert set(result) == {
        "doc-001::chunk-0000",
        "doc-001::chunk-0002",
    }

    assert result["doc-001::chunk-0000"].text == (
        "First evidence text."
    )

    assert result["doc-001::chunk-0002"].text == (
        "Third evidence text."
    )


def test_get_chunks_by_id_ignores_missing_ids(
    tmp_path: Path,
) -> None:
    chunks = [
        make_chunk(
            chunk_id="doc-001::chunk-0000",
        ),
    ]

    append_unique_chunks(
        chunks,
        chunk_store_dir=tmp_path,
    )

    result = get_chunks_by_id(
        [
            "doc-001::chunk-0000",
            "does-not-exist",
        ],
        chunk_store_dir=tmp_path,
    )

    assert set(result) == {
        "doc-001::chunk-0000",
    }


def test_get_chunks_by_id_empty_input(
    tmp_path: Path,
) -> None:
    result = get_chunks_by_id(
        [],
        chunk_store_dir=tmp_path,
    )

    assert result == {}