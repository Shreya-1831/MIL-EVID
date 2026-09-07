from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.core.exceptions import IndexNotBuiltError, IndexPersistenceError
from app.domain.enums import SourceType
from app.domain.models.evidence import EvidenceDocument
from app.modules.retrieval.bm25_index import BM25Index, tokenize
from app.repositories.chunk_file_store import replace_chunks


def make_chunk(
    *,
    chunk_id: str,
    text: str,
    source: str = "Test Source",
) -> EvidenceDocument:
    return EvidenceDocument(
        id=chunk_id,
        document_id="doc-001",
        chunk_index=0,
        text=text,
        source=source,
        source_type=SourceType.UCDP,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


FIXTURE_CHUNKS = [
    make_chunk(
        chunk_id="chunk-001",
        text="Peacekeeping forces were deployed to the border region.",
    ),
    make_chunk(
        chunk_id="chunk-002",
        text="The ceasefire agreement was signed by both military commanders.",
    ),
    make_chunk(
        chunk_id="chunk-003",
        text="Humanitarian aid convoys reached the affected civilian population.",
    ),
]


def build_fixture_store(tmp_path: Path) -> Path:
    chunk_store_dir = tmp_path / "chunks"
    replace_chunks(
        FIXTURE_CHUNKS,
        chunk_store_dir=chunk_store_dir,
    )
    return chunk_store_dir


# ---------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------


def test_tokenize_lowercases_and_splits_on_non_alphanumeric() -> None:
    assert tokenize("Ceasefire-Agreement, signed!") == [
        "ceasefire",
        "agreement",
        "signed",
    ]


def test_tokenize_empty_string_returns_empty_list() -> None:
    assert tokenize("") == []


def test_tokenize_unicode_text() -> None:
    tokens = tokenize("Civilian protection — Ukraine")
    assert "civilian" in tokens
    assert "protection" in tokens
    assert "ukraine" in tokens


# ---------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------


def test_build_creates_index_over_all_chunks(tmp_path: Path) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)

    index = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )

    assert index.size == len(FIXTURE_CHUNKS)


def test_build_raises_on_empty_chunk_store(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty_chunks"
    empty_dir.mkdir()

    with pytest.raises(IndexPersistenceError):
        BM25Index.build(
            chunk_store_dir=empty_dir,
        )


def test_build_produces_corpus_fingerprint(tmp_path: Path) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)

    index = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )

    assert index.corpus_fingerprint
    assert len(index.corpus_fingerprint) == 64


def test_build_same_corpus_produces_same_fingerprint(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)

    index_a = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )
    index_b = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )

    assert index_a.corpus_fingerprint == index_b.corpus_fingerprint


def test_build_changed_corpus_produces_different_fingerprint(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)

    first = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )

    updated_chunks = FIXTURE_CHUNKS + [
        make_chunk(
            chunk_id="chunk-004",
            text="A fourth evidence chunk.",
        )
    ]

    replace_chunks(
        updated_chunks,
        chunk_store_dir=chunk_store_dir,
    )

    rebuilt = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )

    assert (
        rebuilt.corpus_fingerprint
        != first.corpus_fingerprint
    )


# ---------------------------------------------------------------------
# Save / Load
# ---------------------------------------------------------------------


def test_save_then_load_preserves_size_and_mapping(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)
    index_dir = tmp_path / "indexes" / "bm25"

    index = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )

    index.save(index_dir=index_dir)

    assert BM25Index.exists(
        index_dir=index_dir,
    )

    loaded = BM25Index.load(
        index_dir=index_dir,
    )

    assert loaded.size == index.size
    assert (
        loaded.corpus_fingerprint
        == index.corpus_fingerprint
    )

    results = loaded.search(
        "ceasefire",
        top_k=5,
    )

    assert results
    assert results[0].chunk_id == "chunk-002"


def test_load_raises_when_index_not_built(
    tmp_path: Path,
) -> None:
    missing_dir = tmp_path / "does_not_exist"

    with pytest.raises(IndexNotBuiltError):
        BM25Index.load(
            index_dir=missing_dir,
        )


def test_save_is_safe_to_rerun(tmp_path: Path) -> None:
    """Saving the same index twice must not corrupt it."""
    chunk_store_dir = build_fixture_store(tmp_path)
    index_dir = tmp_path / "indexes" / "bm25"

    index = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )

    index.save(index_dir=index_dir)
    index.save(index_dir=index_dir)

    loaded = BM25Index.load(
        index_dir=index_dir,
    )

    assert loaded.size == index.size
    assert (
        loaded.corpus_fingerprint
        == index.corpus_fingerprint
    )


def test_rebuild_reflects_updated_chunk_store(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)
    index_dir = tmp_path / "indexes" / "bm25"

    first = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )
    first.save(index_dir=index_dir)

    updated_chunks = FIXTURE_CHUNKS + [
        make_chunk(
            chunk_id="chunk-004",
            text="A fourth evidence chunk.",
        )
    ]

    replace_chunks(
        updated_chunks,
        chunk_store_dir=chunk_store_dir,
    )

    rebuilt = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )
    rebuilt.save(index_dir=index_dir)

    loaded = BM25Index.load(
        index_dir=index_dir,
    )

    assert loaded.size == len(FIXTURE_CHUNKS) + 1
    assert (
        loaded.corpus_fingerprint
        != first.corpus_fingerprint
    )


def test_saved_index_contains_single_persistent_payload(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)
    index_dir = tmp_path / "indexes" / "bm25"

    index = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )
    index.save(index_dir=index_dir)

    assert (index_dir / "bm25_index.pkl").is_file()
    assert not (index_dir / "chunk_ids.json").exists()


# ---------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------


def test_search_returns_relevant_chunk_first(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)

    index = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )

    results = index.search(
        "humanitarian aid",
        top_k=5,
    )

    assert results
    assert results[0].chunk_id == "chunk-003"


def test_search_respects_top_k(tmp_path: Path) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)

    index = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )

    results = index.search(
        "the",
        top_k=1,
    )

    assert len(results) <= 1


@pytest.mark.parametrize(
    "top_k",
    [0, -1, -10],
)
def test_search_non_positive_top_k_returns_empty(
    tmp_path: Path,
    top_k: int,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)

    index = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )

    assert (
        index.search(
            "ceasefire",
            top_k=top_k,
        )
        == []
    )


def test_search_empty_query_returns_no_results(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)

    index = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )

    assert index.search("", top_k=5) == []
    assert index.search("   ", top_k=5) == []


def test_search_query_with_no_matching_terms_returns_empty(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)

    index = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )

    results = index.search(
        "zzz_no_such_term_qqq",
        top_k=5,
    )

    assert results == []


def test_search_query_with_only_punctuation_returns_empty(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)

    index = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )

    assert index.search(
        "???!!!",
        top_k=5,
    ) == []


def test_search_ordering_is_deterministic_across_runs(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)

    index_a = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )
    index_b = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )

    results_a = index_a.search(
        "military ceasefire",
        top_k=5,
    )
    results_b = index_b.search(
        "military ceasefire",
        top_k=5,
    )

    assert [r.chunk_id for r in results_a] == [
        r.chunk_id for r in results_b
    ]

    assert [r.score for r in results_a] == [
        r.score for r in results_b
    ]


def test_search_chunk_id_mapping_matches_source_text(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)

    index = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )

    results = index.search(
        "convoys civilian",
        top_k=1,
    )

    assert results
    assert results[0].chunk_id == "chunk-003"


# ---------------------------------------------------------------------
# Persistence integrity
# ---------------------------------------------------------------------


def test_load_rejects_corrupted_index(
    tmp_path: Path,
) -> None:
    index_dir = tmp_path / "indexes" / "bm25"
    index_dir.mkdir(parents=True)

    index_path = index_dir / "bm25_index.pkl"
    index_path.write_bytes(b"this is not a valid pickle")

    with pytest.raises(IndexPersistenceError):
        BM25Index.load(
            index_dir=index_dir,
        )


def test_load_rejects_invalid_payload(
    tmp_path: Path,
) -> None:
    import pickle

    index_dir = tmp_path / "indexes" / "bm25"
    index_dir.mkdir(parents=True)

    index_path = index_dir / "bm25_index.pkl"

    with index_path.open("wb") as file:
        pickle.dump(
            {"invalid": "payload"},
            file,
        )

    with pytest.raises(IndexPersistenceError):
        BM25Index.load(
            index_dir=index_dir,
        )