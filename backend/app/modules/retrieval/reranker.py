"""
Cross-encoder reranking for hybrid retrieval candidates.

The reranker takes candidate chunks produced by the hybrid BM25 + FAISS
retriever and scores each (query, chunk_text) pair using a cross-encoder.

The dense retrieval embedding model is NOT used here.

Dense retrieval:
    sentence-transformers/all-MiniLM-L6-v2

Reranking:
    cross-encoder/ms-marco-MiniLM-L-6-v2
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

import numpy as np
from sentence_transformers import CrossEncoder

from app.modules.retrieval.hybrid_retriever import HybridSearchResult


DEFAULT_RERANK_BATCH_SIZE = 32


class CrossEncoderModelProtocol(Protocol):
    """Interface required from a cross-encoder model."""

    def predict(
        self,
        sentences: Sequence[Sequence[str]],
        *,
        batch_size: int = 32,
        show_progress_bar: bool = False,
    ) -> Any:
        ...


@dataclass(frozen=True)
class RerankedSearchResult:
    """A single cross-encoder reranked evidence result."""

    chunk_id: str
    score: float
    original_rrf_score: float
    ranks: tuple[int, ...]


class CrossEncoderReranker:
    """Rerank hybrid retrieval candidates with a cross-encoder."""

    def __init__(
        self,
        *,
        model_name: str,
        model: CrossEncoderModelProtocol | None = None,
        batch_size: int = DEFAULT_RERANK_BATCH_SIZE,
    ) -> None:
        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError(
                "model_name must be a non-empty string"
            )

        if batch_size <= 0:
            raise ValueError(
                "batch_size must be greater than 0"
            )

        self._model_name = model_name
        self._batch_size = batch_size
        self._model = (
            model
            if model is not None
            else CrossEncoder(model_name)
        )

    @property
    def model_name(self) -> str:
        """Return the configured cross-encoder model name."""
        return self._model_name

    @property
    def batch_size(self) -> int:
        """Return the configured prediction batch size."""
        return self._batch_size

    def rerank(
        self,
        *,
        query: str,
        candidates: Sequence[HybridSearchResult],
        chunk_texts: dict[str, str],
        top_k: int = 20,
    ) -> list[RerankedSearchResult]:
        """Rerank hybrid candidates using query/chunk text pairs."""

        if top_k <= 0:
            return []

        if not query or not query.strip():
            return []

        if not candidates:
            return []

        pairs: list[list[str]] = []
        valid_candidates: list[HybridSearchResult] = []

        for candidate in candidates:
            if not isinstance(candidate.chunk_id, str):
                raise ValueError(
                    "candidate chunk_id must be a string"
                )

            if candidate.chunk_id not in chunk_texts:
                raise KeyError(
                    f"Missing chunk text for '{candidate.chunk_id}'"
                )

            text = chunk_texts[candidate.chunk_id]

            if not isinstance(text, str):
                raise ValueError(
                    f"Chunk text for '{candidate.chunk_id}' "
                    "must be a string"
                )

            if not text.strip():
                continue

            pairs.append(
                [
                    query,
                    text,
                ]
            )

            valid_candidates.append(candidate)

        if not pairs:
            return []

        scores = self._model.predict(
            pairs,
            batch_size=self._batch_size,
            show_progress_bar=False,
        )

        scores_array = np.asarray(
            scores,
            dtype=np.float32,
        ).reshape(-1)

        if len(scores_array) != len(valid_candidates):
            raise ValueError(
                "Cross-encoder returned an unexpected number "
                "of scores: "
                f"expected={len(valid_candidates)}, "
                f"got={len(scores_array)}"
            )

        if not np.all(np.isfinite(scores_array)):
            raise ValueError(
                "Cross-encoder returned non-finite scores"
            )

        results = [
            RerankedSearchResult(
                chunk_id=candidate.chunk_id,
                score=float(score),
                original_rrf_score=candidate.score,
                ranks=candidate.ranks,
            )
            for candidate, score in zip(
                valid_candidates,
                scores_array,
            )
        ]

        # Highest cross-encoder score first.
        # Chunk ID provides deterministic ordering for exact ties.
        results.sort(
            key=lambda result: (
                -result.score,
                result.chunk_id,
            )
        )

        return results[:top_k]