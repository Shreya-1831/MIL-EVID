from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import faiss
import numpy as np
import pytest

from app.core.exceptions import (
    IndexNotBuiltError,
    IndexPersistenceError,
)
from app.domain.enums import SourceType
from app.domain.models.evidence import EvidenceDocument
from app.modules.retrieval.embedding_model import get_embedding_model
from app.modules.retrieval.faiss_index import FaissIndex
from app.repositories.chunk_file_store import replace_chunks


TEST_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def make_chunk(
    *,
    chunk_id: str,
    text: str,
) -> EvidenceDocument:
    return EvidenceDocument(
        id=chunk_id,
        document_id="doc-001",
        chunk_index=0,
        text=text,
        source="Test Source",
        source_type=SourceType.UCDP,
        created_at=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
    )


FIXTURE_CHUNKS = [
    make_chunk(
        chunk_id="chunk-001",
        text=(
            "Peacekeeping troops were stationed along "
            "the disputed border."
        ),
    ),
    make_chunk(
        chunk_id="chunk-002",
        text=(
            "A formal truce was signed between "
            "the two rival factions."
        ),
    ),
    make_chunk(
        chunk_id="chunk-003",
        text=(
            "Relief organizations delivered food "
            "and medicine to refugees."
        ),
    ),
]


@pytest.fixture(scope="module", autouse=True)
def _warm_model_cache():
    """Load the real lightweight model once for this test module."""
    get_embedding_model.cache_clear()
    get_embedding_model(TEST_MODEL_NAME)

    yield

    get_embedding_model.cache_clear()


def build_fixture_store(tmp_path: Path) -> Path:
    chunk_store_dir = tmp_path / "chunks"

    replace_chunks(
        FIXTURE_CHUNKS,
        chunk_store_dir=chunk_store_dir,
    )

    return chunk_store_dir


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def test_build_creates_index_over_all_chunks(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)

    index = FaissIndex.build(
        chunk_store_dir=chunk_store_dir,
        model_name=TEST_MODEL_NAME,
    )

    assert index.size == len(FIXTURE_CHUNKS)
    assert index.model_name == TEST_MODEL_NAME
    assert index.dimension == 384


def test_build_raises_on_empty_chunk_store(
    tmp_path: Path,
) -> None:
    empty_dir = tmp_path / "empty_chunks"
    empty_dir.mkdir()

    with pytest.raises(IndexPersistenceError):
        FaissIndex.build(
            chunk_store_dir=empty_dir,
            model_name=TEST_MODEL_NAME,
        )


def test_build_batches_smaller_than_batch_size(
    tmp_path: Path,
) -> None:
    """Non-multiple chunk count must still index every chunk."""

    chunk_store_dir = build_fixture_store(tmp_path)

    index = FaissIndex.build(
        chunk_store_dir=chunk_store_dir,
        model_name=TEST_MODEL_NAME,
        batch_size=2,
    )

    assert index.size == len(FIXTURE_CHUNKS)


@pytest.mark.parametrize(
    "batch_size",
    [0, -1, -10],
)
def test_build_rejects_invalid_batch_size(
    tmp_path: Path,
    batch_size: int,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)

    with pytest.raises(
        ValueError,
        match="batch_size must be greater than 0",
    ):
        FaissIndex.build(
            chunk_store_dir=chunk_store_dir,
            model_name=TEST_MODEL_NAME,
            batch_size=batch_size,
        )


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------


def test_constructor_rejects_vector_id_count_mismatch() -> None:
    index = faiss.IndexFlatIP(3)

    index.add(
        np.array(
            [[1.0, 0.0, 0.0]],
            dtype=np.float32,
        )
    )

    with pytest.raises(
        ValueError,
        match="does not match chunk ID count",
    ):
        FaissIndex(
            index=index,
            chunk_ids=[],
            model_name=TEST_MODEL_NAME,
        )


def test_constructor_rejects_duplicate_chunk_ids() -> None:
    index = faiss.IndexFlatIP(3)

    index.add(
        np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
            ],
            dtype=np.float32,
        )
    )

    with pytest.raises(
        ValueError,
        match="must not contain duplicates",
    ):
        FaissIndex(
            index=index,
            chunk_ids=[
                "chunk-001",
                "chunk-001",
            ],
            model_name=TEST_MODEL_NAME,
        )


def test_constructor_rejects_empty_model_name() -> None:
    index = faiss.IndexFlatIP(3)

    with pytest.raises(
        ValueError,
        match="non-empty",
    ):
        FaissIndex(
            index=index,
            chunk_ids=[],
            model_name="",
        )


# ---------------------------------------------------------------------------
# Save / Load
# ---------------------------------------------------------------------------


def test_save_then_load_preserves_size_and_model(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)
    index_dir = tmp_path / "indexes" / "faiss"

    index = FaissIndex.build(
        chunk_store_dir=chunk_store_dir,
        model_name=TEST_MODEL_NAME,
    )

    index.save(index_dir=index_dir)

    assert FaissIndex.exists(
        index_dir=index_dir,
    )

    loaded = FaissIndex.load(
        index_dir=index_dir,
    )

    assert loaded.size == index.size
    assert loaded.model_name == TEST_MODEL_NAME
    assert loaded.dimension == index.dimension


def test_save_then_load_preserves_chunk_mapping(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)
    index_dir = tmp_path / "indexes" / "faiss"

    index = FaissIndex.build(
        chunk_store_dir=chunk_store_dir,
        model_name=TEST_MODEL_NAME,
    )

    index.save(index_dir=index_dir)

    loaded = FaissIndex.load(
        index_dir=index_dir,
    )

    assert loaded._chunk_ids == index._chunk_ids


def test_load_raises_when_index_not_built(
    tmp_path: Path,
) -> None:
    missing_dir = tmp_path / "does_not_exist"

    with pytest.raises(IndexNotBuiltError):
        FaissIndex.load(
            index_dir=missing_dir,
        )


def test_save_is_safe_to_rerun(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)
    index_dir = tmp_path / "indexes" / "faiss"

    index = FaissIndex.build(
        chunk_store_dir=chunk_store_dir,
        model_name=TEST_MODEL_NAME,
    )

    index.save(index_dir=index_dir)
    index.save(index_dir=index_dir)

    loaded = FaissIndex.load(
        index_dir=index_dir,
    )

    assert loaded.size == index.size
    assert loaded._chunk_ids == index._chunk_ids


def test_rebuild_reflects_updated_chunk_store(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)
    index_dir = tmp_path / "indexes" / "faiss"

    first = FaissIndex.build(
        chunk_store_dir=chunk_store_dir,
        model_name=TEST_MODEL_NAME,
    )

    first.save(index_dir=index_dir)

    replace_chunks(
        FIXTURE_CHUNKS
        + [
            make_chunk(
                chunk_id="chunk-004",
                text="A fourth chunk.",
            )
        ],
        chunk_store_dir=chunk_store_dir,
    )

    rebuilt = FaissIndex.build(
        chunk_store_dir=chunk_store_dir,
        model_name=TEST_MODEL_NAME,
    )

    rebuilt.save(index_dir=index_dir)

    loaded = FaissIndex.load(
        index_dir=index_dir,
    )

    assert loaded.size == len(FIXTURE_CHUNKS) + 1


def test_saved_metadata_contains_expected_fields(
    tmp_path: Path,
) -> None:
    index = FaissIndex(
        index=faiss.IndexFlatIP(3),
        chunk_ids=[],
        model_name="test-model",
    )

    index.save(index_dir=tmp_path)

    metadata = json.loads(
        (tmp_path / "metadata.json").read_text(
            encoding="utf-8",
        )
    )

    assert metadata["version"] == 1
    assert metadata["model_name"] == "test-model"
    assert metadata["dimension"] == 3
    assert metadata["chunk_ids"] == []


def test_load_rejects_wrong_metadata_version(
    tmp_path: Path,
) -> None:
    index = make_small_index(
        ["chunk-a"],
    )

    index.save(index_dir=tmp_path)

    metadata_path = tmp_path / "metadata.json"

    metadata = json.loads(
        metadata_path.read_text(
            encoding="utf-8",
        )
    )

    metadata["version"] = 999

    metadata_path.write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    with pytest.raises(IndexPersistenceError):
        FaissIndex.load(index_dir=tmp_path)


def test_load_rejects_dimension_mismatch(
    tmp_path: Path,
) -> None:
    index = make_small_index(
        ["chunk-a"],
    )

    index.save(index_dir=tmp_path)

    metadata_path = tmp_path / "metadata.json"

    metadata = json.loads(
        metadata_path.read_text(
            encoding="utf-8",
        )
    )

    metadata["dimension"] = 999

    metadata_path.write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    with pytest.raises(IndexPersistenceError):
        FaissIndex.load(index_dir=tmp_path)


def test_load_rejects_corrupted_metadata(
    tmp_path: Path,
) -> None:
    index = make_small_index(
        ["chunk-a"],
    )

    index.save(index_dir=tmp_path)

    (tmp_path / "metadata.json").write_text(
        "{invalid json",
        encoding="utf-8",
    )

    with pytest.raises(IndexPersistenceError):
        FaissIndex.load(index_dir=tmp_path)


def test_load_rejects_chunk_id_count_mismatch(
    tmp_path: Path,
) -> None:
    index = make_small_index(
        ["chunk-a"],
    )

    index.save(index_dir=tmp_path)

    metadata_path = tmp_path / "metadata.json"

    metadata = json.loads(
        metadata_path.read_text(
            encoding="utf-8",
        )
    )

    metadata["chunk_ids"] = []

    metadata_path.write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    with pytest.raises(IndexPersistenceError):
        FaissIndex.load(index_dir=tmp_path)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def test_search_returns_semantically_relevant_chunk_first(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)

    index = FaissIndex.build(
        chunk_store_dir=chunk_store_dir,
        model_name=TEST_MODEL_NAME,
    )

    results = index.search(
        "humanitarian relief for displaced people",
        top_k=3,
    )

    assert results
    assert results[0].chunk_id == "chunk-003"


def test_search_respects_top_k(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)

    index = FaissIndex.build(
        chunk_store_dir=chunk_store_dir,
        model_name=TEST_MODEL_NAME,
    )

    results = index.search(
        "border troops",
        top_k=1,
    )

    assert len(results) == 1


def test_search_empty_query_returns_no_results(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)

    index = FaissIndex.build(
        chunk_store_dir=chunk_store_dir,
        model_name=TEST_MODEL_NAME,
    )

    assert index.search(
        "",
        top_k=5,
    ) == []

    assert index.search(
        "   ",
        top_k=5,
    ) == []


@pytest.mark.parametrize(
    "top_k",
    [0, -1, -10],
)
def test_search_non_positive_top_k_returns_no_results(
    tmp_path: Path,
    top_k: int,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)

    index = FaissIndex.build(
        chunk_store_dir=chunk_store_dir,
        model_name=TEST_MODEL_NAME,
    )

    assert index.search(
        "peace and conflict",
        top_k=top_k,
    ) == []


def test_search_top_k_larger_than_corpus_returns_all(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)

    index = FaissIndex.build(
        chunk_store_dir=chunk_store_dir,
        model_name=TEST_MODEL_NAME,
    )

    results = index.search(
        "peace and conflict",
        top_k=1000,
    )

    assert len(results) == len(FIXTURE_CHUNKS)


def test_search_chunk_id_mapping_matches_source_text(
    tmp_path: Path,
) -> None:
    chunk_store_dir = build_fixture_store(tmp_path)

    index = FaissIndex.build(
        chunk_store_dir=chunk_store_dir,
        model_name=TEST_MODEL_NAME,
    )

    results = index.search(
        "truce signed between factions",
        top_k=1,
    )

    assert results[0].chunk_id == "chunk-002"


def test_search_uses_same_model_after_load(
    tmp_path: Path,
    monkeypatch,
) -> None:
    index = make_small_index(
        ["chunk-a"],
        model_name="persisted-model",
    )

    index.save(index_dir=tmp_path)

    loaded = FaissIndex.load(
        index_dir=tmp_path,
    )

    requested_models = []

    class FakeModel:
        def get_sentence_embedding_dimension(self):
            return 3

        def encode(self, texts, **kwargs):
            return np.array(
                [[1.0, 0.0, 0.0]],
                dtype=np.float32,
            )

    def fake_get_model(model_name):
        requested_models.append(model_name)
        return FakeModel()

    monkeypatch.setattr(
        "app.modules.retrieval.faiss_index.get_embedding_model",
        fake_get_model,
    )

    loaded.search(
        "query",
        top_k=1,
    )

    assert requested_models == ["persisted-model"]


# ---------------------------------------------------------------------------
# Small in-memory helpers for fast validation tests
# ---------------------------------------------------------------------------


def make_small_index(
    chunk_ids: list[str],
    model_name: str = "test-model",
) -> FaissIndex:
    dimension = 3

    index = faiss.IndexFlatIP(dimension)

    vectors = np.zeros(
        (len(chunk_ids), dimension),
        dtype=np.float32,
    )

    for position in range(len(chunk_ids)):
        vectors[position, position % dimension] = 1.0

    if len(chunk_ids):
        index.add(vectors)

    return FaissIndex(
        index=index,
        chunk_ids=chunk_ids,
        model_name=model_name,
    )