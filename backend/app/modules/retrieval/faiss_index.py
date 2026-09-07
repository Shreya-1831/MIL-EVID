"""FAISS dense (semantic) index over evidence chunks.

Embeddings are generated with the configured Sentence Transformer and
indexed using FAISS IndexFlatIP.

Because embeddings are L2-normalized, inner product is equivalent to
cosine similarity.

The index stores:
    - FAISS vectors
    - position-aligned chunk IDs
    - embedding model name
    - embedding dimension
    - persistence format version

Chunk text is read only from the local JSONL chunk store.
PostgreSQL is not used for vector construction.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import faiss

from app.core.exceptions import IndexNotBuiltError, IndexPersistenceError
from app.core.logging import get_logger
from app.modules.retrieval.embedding_model import (
    embed_texts,
    get_embedding_model,
)
from app.repositories.chunk_file_store import iter_all_chunks

logger = get_logger(__name__)

_INDEX_FILENAME = "faiss_index.bin"
_METADATA_FILENAME = "metadata.json"

_PERSISTENCE_VERSION = 1
EMBEDDING_BATCH_SIZE = 64


@dataclass(frozen=True)
class DenseSearchResult:
    """A single dense semantic search hit."""

    chunk_id: str
    score: float


class FaissIndex:
    """A FAISS dense index plus its chunk-ID mapping."""

    def __init__(
        self,
        *,
        index: faiss.Index,
        chunk_ids: list[str],
        model_name: str,
    ) -> None:
        if not isinstance(index, faiss.Index):
            raise ValueError("index must be a FAISS index")

        if not isinstance(chunk_ids, list):
            raise ValueError("chunk_ids must be a list")

        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError("model_name must be a non-empty string")

        if index.ntotal != len(chunk_ids):
            raise ValueError(
                "FAISS vector count does not match chunk ID count: "
                f"vectors={index.ntotal}, chunk_ids={len(chunk_ids)}"
            )

        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("chunk_ids must not contain duplicates")

        if index.d > 0 and index.ntotal > 0:
            dimension = index.d
            if dimension <= 0:
                raise ValueError("FAISS index has an invalid dimension")

        self._index = index
        self._chunk_ids = list(chunk_ids)
        self._model_name = model_name

    @property
    def size(self) -> int:
        """Number of chunks/vectors in the index."""
        return len(self._chunk_ids)

    @property
    def model_name(self) -> str:
        """Embedding model used to build the index."""
        return self._model_name

    @property
    def dimension(self) -> int:
        """Embedding dimensionality of the FAISS index."""
        return self._index.d

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    @classmethod
    def build(
        cls,
        *,
        chunk_store_dir: Path,
        model_name: str,
        batch_size: int = EMBEDDING_BATCH_SIZE,
        progress_callback=None,
    ) -> "FaissIndex":
        """Build a FAISS index from the local JSONL chunk store.

        Chunks are streamed from disk and encoded in batches, avoiding
        materialization of the complete corpus in memory.
        """
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than 0")

        model = get_embedding_model(model_name)

        dimension = model.get_sentence_embedding_dimension()

        if dimension is None or dimension <= 0:
            raise IndexPersistenceError(
                "Embedding model returned an invalid dimension"
            )

        index = faiss.IndexFlatIP(dimension)

        chunk_ids: list[str] = []
        pending_texts: list[str] = []
        pending_ids: list[str] = []

        def flush_batch() -> None:
            if not pending_texts:
                return

            embeddings = embed_texts(
                pending_texts,
                model=model,
                batch_size=batch_size,
            )

            if embeddings.shape != (
                len(pending_texts),
                dimension,
            ):
                raise IndexPersistenceError(
                    "Embedding output shape does not match "
                    f"expected ({len(pending_texts)}, {dimension}); "
                    f"got {embeddings.shape}"
                )

            index.add(embeddings)
            chunk_ids.extend(pending_ids)
            if progress_callback is not None:
                progress_callback(len(chunk_ids))

        for chunk in iter_all_chunks(chunk_store_dir):
            if not isinstance(chunk.id, str) or not chunk.id:
                raise IndexPersistenceError(
                    "Chunk store contains a chunk with an invalid ID"
                )

            if chunk.id in chunk_ids or chunk.id in pending_ids:
                raise IndexPersistenceError(
                    f"Duplicate chunk ID encountered: '{chunk.id}'"
                )

            pending_texts.append(chunk.text)
            pending_ids.append(chunk.id)

            if len(pending_texts) >= batch_size:
                flush_batch()
                pending_texts.clear()
                pending_ids.clear()

        flush_batch()

        if not chunk_ids:
            raise IndexPersistenceError(
                f"No chunks found under '{chunk_store_dir}'; "
                "cannot build FAISS index."
            )

        if index.ntotal != len(chunk_ids):
            raise IndexPersistenceError(
                "FAISS vector count does not match chunk ID count "
                f"after build: vectors={index.ntotal}, "
                f"chunk_ids={len(chunk_ids)}"
            )

        logger.info(
            "faiss_index_built",
            chunk_count=len(chunk_ids),
            dimension=dimension,
            model_name=model_name,
        )

        return cls(
            index=index,
            chunk_ids=chunk_ids,
            model_name=model_name,
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @classmethod
    def exists(cls, *, index_dir: Path) -> bool:
        """Return whether both persisted FAISS files exist."""
        return (
            (index_dir / _INDEX_FILENAME).is_file()
            and (index_dir / _METADATA_FILENAME).is_file()
        )

    def save(self, *, index_dir: Path) -> None:
        """Persist the FAISS index and metadata."""
        index_dir.mkdir(parents=True, exist_ok=True)

        index_path = index_dir / _INDEX_FILENAME
        metadata_path = index_dir / _METADATA_FILENAME

        tmp_index_path = index_dir / f"{_INDEX_FILENAME}.tmp"
        tmp_metadata_path = index_dir / f"{_METADATA_FILENAME}.tmp"

        metadata = {
            "version": _PERSISTENCE_VERSION,
            "model_name": self._model_name,
            "dimension": self.dimension,
            "chunk_ids": self._chunk_ids,
        }

        try:
            faiss.write_index(
                self._index,
                str(tmp_index_path),
            )

            with tmp_metadata_path.open(
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    metadata,
                    file,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )

            # Replace both files only after both temporary files have
            # been successfully written.
            tmp_index_path.replace(index_path)
            tmp_metadata_path.replace(metadata_path)

        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            tmp_index_path.unlink(missing_ok=True)
            tmp_metadata_path.unlink(missing_ok=True)

            raise IndexPersistenceError(
                f"Failed to save FAISS index to '{index_dir}': {exc}"
            ) from exc

        logger.info(
            "faiss_index_saved",
            index_dir=str(index_dir),
            chunk_count=self.size,
            dimension=self.dimension,
        )

    @classmethod
    def load(cls, *, index_dir: Path) -> "FaissIndex":
        """Load a previously persisted FAISS index."""
        if not cls.exists(index_dir=index_dir):
            raise IndexNotBuiltError(
                f"FAISS index not found at '{index_dir}'. "
                "Run scripts/build_indexes.py first."
            )

        index_path = index_dir / _INDEX_FILENAME
        metadata_path = index_dir / _METADATA_FILENAME

        try:
            index = faiss.read_index(str(index_path))

            with metadata_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                metadata = json.load(file)

            if not isinstance(metadata, dict):
                raise ValueError("metadata must be a JSON object")

            if metadata.get("version") != _PERSISTENCE_VERSION:
                raise ValueError(
                    "unsupported FAISS metadata version"
                )

            model_name = metadata["model_name"]
            dimension = metadata["dimension"]
            chunk_ids = metadata["chunk_ids"]

            if not isinstance(model_name, str):
                raise ValueError("model_name must be a string")

            if not isinstance(dimension, int):
                raise ValueError("dimension must be an integer")

            if dimension != index.d:
                raise ValueError(
                    "metadata dimension does not match FAISS index: "
                    f"metadata={dimension}, index={index.d}"
                )

            if not isinstance(chunk_ids, list):
                raise ValueError("chunk_ids must be a list")

        except (
            OSError,
            RuntimeError,
            ValueError,
            KeyError,
            TypeError,
            json.JSONDecodeError,
        ) as exc:
            raise IndexPersistenceError(
                f"Failed to load FAISS index from '{index_dir}': {exc}"
            ) from exc

        try:
            return cls(
                index=index,
                chunk_ids=chunk_ids,
                model_name=model_name,
            )
        except ValueError as exc:
            raise IndexPersistenceError(
                f"Invalid FAISS index metadata in '{index_dir}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
    ) -> list[DenseSearchResult]:
        """Return chunks ranked by semantic similarity."""

        if top_k <= 0:
            return []

        if not query or not query.strip():
            return []

        if self.size == 0:
            return []

        model = get_embedding_model(self._model_name)

        query_embedding = embed_texts(
            [query],
            model=model,
            batch_size=1,
        )

        k = min(top_k, self.size)

        scores, indices = self._index.search(
            query_embedding,
            k,
        )

        hits: list[tuple[str, float]] = []

        for idx, score in zip(
            indices[0],
            scores[0],
        ):
            if idx == -1:
                continue

            if idx < 0 or idx >= len(self._chunk_ids):
                raise IndexPersistenceError(
                    "FAISS returned an index outside the chunk-ID mapping"
                )

            hits.append(
                (
                    self._chunk_ids[idx],
                    float(score),
                )
            )

        # Deterministic ordering for exact score ties.
        hits.sort(
            key=lambda pair: (-pair[1], pair[0])
        )

        return [
            DenseSearchResult(
                chunk_id=chunk_id,
                score=score,
            )
            for chunk_id, score in hits[:top_k]
        ]