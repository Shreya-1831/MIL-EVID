"""BM25 keyword index over evidence chunks.

Builds a rank_bm25.BM25Okapi index directly from the local JSONL
chunk store. PostgreSQL is not used as the source of chunk text.

Chunk identity is tracked using a position-aligned list of chunk IDs:

    chunk_ids[i] <-> BM25 document i

A SHA-256 corpus fingerprint is persisted with the index so that
future retrieval code can detect an index built from a different
chunk corpus.
"""

from __future__ import annotations

import hashlib
import pickle
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

from app.core.exceptions import IndexNotBuiltError, IndexPersistenceError
from app.core.logging import get_logger
from app.repositories.chunk_file_store import iter_all_chunks

logger = get_logger(__name__)

_INDEX_FILENAME = "bm25_index.pkl"

# Unicode-aware tokenizer:
# - lowercases text
# - keeps letters/numbers from non-English text
# - removes punctuation
#
# This is intentionally simple so index-time and query-time
# tokenization are guaranteed to use the same rules.
_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Tokenize text for BM25 indexing and querying."""
    if not isinstance(text, str):
        return []

    return _TOKEN_RE.findall(text.lower())


def _update_corpus_hash(
    hasher: hashlib._Hash,
    chunk_id: str,
    text: str,
) -> None:
    """Update the corpus fingerprint with one chunk.

    Length-prefixing prevents ambiguous concatenations such as:

        ("ab", "c") != ("a", "bc")

    from accidentally producing the same byte sequence.
    """
    chunk_id_bytes = chunk_id.encode("utf-8")
    text_bytes = text.encode("utf-8")

    hasher.update(len(chunk_id_bytes).to_bytes(8, "big"))
    hasher.update(chunk_id_bytes)
    hasher.update(len(text_bytes).to_bytes(8, "big"))
    hasher.update(text_bytes)


@dataclass(frozen=True)
class BM25SearchResult:
    """A single BM25 keyword-search hit."""

    chunk_id: str
    score: float


class BM25Index:
    """A built, in-memory BM25 index plus its chunk-ID mapping."""

    def __init__(
        self,
        bm25: BM25Okapi,
        chunk_ids: list[str],
        corpus_fingerprint: str,
    ) -> None:
        if not isinstance(bm25, BM25Okapi):
            raise IndexPersistenceError(
                "Invalid BM25 index object."
            )

        if not isinstance(chunk_ids, list):
            raise IndexPersistenceError(
                "Invalid BM25 chunk-ID mapping."
            )

        if len(chunk_ids) != len(bm25.doc_freqs):
            raise IndexPersistenceError(
                "BM25 index and chunk-ID mapping have different sizes."
            )

        if not isinstance(corpus_fingerprint, str) or not corpus_fingerprint:
            raise IndexPersistenceError(
                "Missing BM25 corpus fingerprint."
            )

        if len(set(chunk_ids)) != len(chunk_ids):
            raise IndexPersistenceError(
                "BM25 chunk-ID mapping contains duplicate chunk IDs."
            )

        self._bm25 = bm25
        self._chunk_ids = chunk_ids
        self._corpus_fingerprint = corpus_fingerprint

    @property
    def size(self) -> int:
        """Number of chunks in the index."""
        return len(self._chunk_ids)

    @property
    def corpus_fingerprint(self) -> str:
        """SHA-256 fingerprint of the corpus used to build the index."""
        return self._corpus_fingerprint

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    @classmethod
    def build(cls, *, chunk_store_dir: Path) -> "BM25Index":
        """Build a BM25 index from all chunks in the local JSONL store.

        Iteration order follows iter_all_chunks(), so an unchanged
        corpus produces the same document ordering and fingerprint.
        """
        chunk_ids: list[str] = []
        tokenized_corpus: list[list[str]] = []

        corpus_hasher = hashlib.sha256()

        for chunk in iter_all_chunks(chunk_store_dir):
            chunk_id = str(chunk.id)
            text = str(chunk.text)

            chunk_ids.append(chunk_id)
            tokenized_corpus.append(tokenize(text))

            _update_corpus_hash(
                corpus_hasher,
                chunk_id,
                text,
            )

        if not chunk_ids:
            raise IndexPersistenceError(
                f"No chunks found under '{chunk_store_dir}'; "
                "cannot build BM25 index."
            )

        bm25 = BM25Okapi(tokenized_corpus)
        corpus_fingerprint = corpus_hasher.hexdigest()

        logger.info(
            "bm25_index_built",
            chunk_count=len(chunk_ids),
            corpus_fingerprint=corpus_fingerprint,
        )

        return cls(
            bm25=bm25,
            chunk_ids=chunk_ids,
            corpus_fingerprint=corpus_fingerprint,
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @classmethod
    def exists(cls, *, index_dir: Path) -> bool:
        """Return whether a persisted BM25 index exists."""
        return (index_dir / _INDEX_FILENAME).is_file()

    def save(self, *, index_dir: Path) -> None:
        """Persist the BM25 index atomically as a single payload."""
        index_dir.mkdir(parents=True, exist_ok=True)

        index_path = index_dir / _INDEX_FILENAME
        tmp_path = index_dir / f"{_INDEX_FILENAME}.tmp"

        payload = {
            "version": 1,
            "bm25": self._bm25,
            "chunk_ids": self._chunk_ids,
            "corpus_fingerprint": self._corpus_fingerprint,
        }

        try:
            with tmp_path.open("wb") as file:
                pickle.dump(
                    payload,
                    file,
                    protocol=pickle.HIGHEST_PROTOCOL,
                )

            tmp_path.replace(index_path)

        except (OSError, pickle.PickleError) as exc:
            tmp_path.unlink(missing_ok=True)

            raise IndexPersistenceError(
                f"Failed to save BM25 index to '{index_dir}': {exc}"
            ) from exc

        logger.info(
            "bm25_index_saved",
            index_dir=str(index_dir),
            chunk_count=self.size,
            corpus_fingerprint=self.corpus_fingerprint,
        )

    @classmethod
    def load(cls, *, index_dir: Path) -> "BM25Index":
        """Load a previously persisted BM25 index."""
        if not cls.exists(index_dir=index_dir):
            raise IndexNotBuiltError(
                f"BM25 index not found at '{index_dir}'. "
                "Run scripts/build_indexes.py first."
            )

        index_path = index_dir / _INDEX_FILENAME

        try:
            with index_path.open("rb") as file:
                payload: Any = pickle.load(file)

        except (OSError, pickle.PickleError, EOFError, ValueError) as exc:
            raise IndexPersistenceError(
                f"Failed to load BM25 index from '{index_dir}': {exc}"
            ) from exc

        if not isinstance(payload, dict):
            raise IndexPersistenceError(
                "Invalid BM25 index payload."
            )

        if payload.get("version") != 1:
            raise IndexPersistenceError(
                "Unsupported BM25 index version."
            )

        bm25 = payload.get("bm25")
        chunk_ids = payload.get("chunk_ids")
        corpus_fingerprint = payload.get("corpus_fingerprint")

        try:
            return cls(
                bm25=bm25,
                chunk_ids=chunk_ids,
                corpus_fingerprint=corpus_fingerprint,
            )
        except (TypeError, IndexPersistenceError) as exc:
            if isinstance(exc, IndexPersistenceError):
                raise

            raise IndexPersistenceError(
                f"Invalid BM25 index contents at '{index_dir}'."
            ) from exc

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
    ) -> list[BM25SearchResult]:
        """Return up to top_k chunks ranked by BM25 score.

        Empty queries or queries containing no indexable tokens return
        an empty list.

        Results are sorted by:
            1. BM25 score descending
            2. chunk ID ascending

        Zero-score results are excluded.
        """
        if top_k <= 0:
            return []

        if not query or not query.strip():
            return []

        tokens = tokenize(query)

        if not tokens or self.size == 0:
            return []

        scores = self._bm25.get_scores(tokens)

        ranked = sorted(
            zip(self._chunk_ids, scores),
            key=lambda pair: (-float(pair[1]), pair[0]),
        )

        results: list[BM25SearchResult] = []

        for chunk_id, score in ranked:
            if score <= 0:
                continue

            results.append(
                BM25SearchResult(
                    chunk_id=chunk_id,
                    score=float(score),
                )
            )

            if len(results) >= top_k:
                break

        return results