"""Cross-encoder reranking for retrieval candidates.

The reranker supports:
- Hybrid BM25 + FAISS candidates
- Dynamic EvidenceDocument candidates such as ACLED events

Dense retrieval:
    sentence-transformers/all-MiniLM-L6-v2

Reranking:
    cross-encoder/ms-marco-MiniLM-L-6-v2
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

import numpy as np
import torch
from sentence_transformers import CrossEncoder

from app.domain.models.evidence import EvidenceDocument
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


@dataclass(frozen=True)
class RerankedEvidence:
    """A cross-encoder reranked EvidenceDocument."""

    evidence: EvidenceDocument
    score: float


class CrossEncoderReranker:
    """Rerank evidence candidates with a cross-encoder."""

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

        device = "cuda" if torch.cuda.is_available() else "cpu"

        self._model = (
            model
            if model is not None
            else CrossEncoder(
                model_name,
                device=device,
            )
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
        """Rerank hybrid retrieval candidates."""

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

        results.sort(
            key=lambda result: (
                -result.score,
                result.chunk_id,
            )
        )

        return results[:top_k]

    def rerank_evidence(
        self,
        *,
        query: str,
        evidence: Sequence[EvidenceDocument],
        top_k: int = 20,
    ) -> list[RerankedEvidence]:
        """Rerank EvidenceDocument objects with the cross-encoder."""

        if top_k <= 0:
            return []

        if not query or not query.strip():
            return []

        if not evidence:
            return []

        pairs: list[list[str]] = []
        valid_evidence: list[EvidenceDocument] = []

        for document in evidence:
            if not isinstance(document.text, str):
                raise ValueError(
                    f"Evidence text for '{document.id}' must be a string"
                )

            if not document.text.strip():
                continue

            pairs.append(
                [
                    query,
                    document.text,
                ]
            )
            valid_evidence.append(document)

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

        if len(scores_array) != len(valid_evidence):
            raise ValueError(
                "Cross-encoder returned an unexpected number "
                "of scores: "
                f"expected={len(valid_evidence)}, "
                f"got={len(scores_array)}"
            )

        if not np.all(np.isfinite(scores_array)):
            raise ValueError(
                "Cross-encoder returned non-finite scores"
            )

        results = [
            RerankedEvidence(
                evidence=document,
                score=float(score),
            )
            for document, score in zip(
                valid_evidence,
                scores_array,
            )
        ]

        results.sort(
            key=lambda result: (
                -result.score,
                result.evidence.id,
            )
        )

        return results[:top_k]