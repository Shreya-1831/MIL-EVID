"""
Hybrid retrieval combining BM25 lexical retrieval and FAISS
semantic retrieval using Reciprocal Rank Fusion.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from app.modules.retrieval.bm25_index import (
    BM25Index,
    BM25SearchResult,
)
from app.modules.retrieval.faiss_index import (
    DenseSearchResult,
    FaissIndex,
)
from app.modules.retrieval.rrf import (
    DEFAULT_RRF_K,
    reciprocal_rank_fusion,
)


class BM25RetrieverProtocol(Protocol):
    """Interface required from a lexical retriever."""

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
    ) -> Sequence[BM25SearchResult]:
        ...


class DenseRetrieverProtocol(Protocol):
    """Interface required from a dense retriever."""

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
    ) -> Sequence[DenseSearchResult]:
        ...


@dataclass(frozen=True)
class HybridSearchResult:
    """A single hybrid retrieval result."""

    chunk_id: str
    score: float
    ranks: tuple[int, ...]


class HybridRetriever:
    """Combine BM25 and dense FAISS retrieval using RRF."""

    def __init__(
        self,
        *,
        bm25_index: BM25RetrieverProtocol,
        faiss_index: DenseRetrieverProtocol,
        rrf_k: int = DEFAULT_RRF_K,
    ) -> None:
        if rrf_k <= 0:
            raise ValueError(
                "rrf_k must be greater than 0"
            )

        self._bm25_index = bm25_index
        self._faiss_index = faiss_index
        self._rrf_k = rrf_k

    @property
    def bm25_index(self) -> BM25RetrieverProtocol:
        """Return the lexical retriever."""
        return self._bm25_index

    @property
    def faiss_index(self) -> DenseRetrieverProtocol:
        """Return the dense retriever."""
        return self._faiss_index

    @property
    def rrf_k(self) -> int:
        """Return the RRF smoothing constant."""
        return self._rrf_k

    @classmethod
    def from_index_dirs(
        cls,
        *,
        bm25_index_dir: Path,
        faiss_index_dir: Path,
        rrf_k: int = DEFAULT_RRF_K,
    ) -> "HybridRetriever":
        """Load BM25 and FAISS indexes from disk."""

        bm25_index = BM25Index.load(
            index_dir=bm25_index_dir,
        )

        faiss_index = FaissIndex.load(
            index_dir=faiss_index_dir,
        )

        return cls(
            bm25_index=bm25_index,
            faiss_index=faiss_index,
            rrf_k=rrf_k,
        )

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        bm25_top_k: int | None = None,
        dense_top_k: int | None = None,
    ) -> list[HybridSearchResult]:
        """Perform hybrid BM25 + dense retrieval with RRF."""

        if top_k <= 0:
            return []

        if not query or not query.strip():
            return []

        bm25_k = (
            bm25_top_k
            if bm25_top_k is not None
            else top_k
        )

        dense_k = (
            dense_top_k
            if dense_top_k is not None
            else top_k
        )

        if bm25_k <= 0:
            raise ValueError(
                "bm25_top_k must be greater than 0"
            )

        if dense_k <= 0:
            raise ValueError(
                "dense_top_k must be greater than 0"
            )

        bm25_results = self._bm25_index.search(
            query,
            top_k=bm25_k,
        )

        dense_results = self._faiss_index.search(
            query,
            top_k=dense_k,
        )

        fused = reciprocal_rank_fusion(
            [
                bm25_results,
                dense_results,
            ],
            top_k=top_k,
            k=self._rrf_k,
        )

        return [
            HybridSearchResult(
                chunk_id=result.chunk_id,
                score=result.score,
                ranks=result.ranks,
            )
            for result in fused
        ]