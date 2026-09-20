"""Perspective-aware retrieval over the existing hybrid retriever."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums import Perspective
from app.modules.retrieval.hybrid_retriever import (
    HybridRetriever,
    HybridSearchResult,
)
from app.modules.retrieval.perspective_query_builder import (
    PerspectiveQueryBuilder,
)


@dataclass(frozen=True)
class PerspectiveRetrievalResult:
    """Hybrid candidates retrieved for a specific perspective."""

    perspective: Perspective
    candidates: tuple[HybridSearchResult, ...]


class PerspectiveAwareRetriever:
    """Retrieve evidence separately for each requested perspective."""

    def __init__(
        self,
        *,
        retriever: HybridRetriever,
        query_builder: PerspectiveQueryBuilder,
        top_k_per_perspective: int = 50,
    ) -> None:
        self._retriever = retriever
        self._query_builder = query_builder
        self._top_k_per_perspective = max(
            1,
            top_k_per_perspective,
        )

    def search(
        self,
        *,
        query: str,
        perspectives: tuple[Perspective, ...],
        top_k: int | None = None,
    ) -> list[HybridSearchResult]:
        """Retrieve and merge candidates across perspectives."""

        retrieval_k = (
            max(1, top_k)
            if top_k is not None
            else self._top_k_per_perspective
        )

        if not perspectives:
            return self._retriever.search(
                query,
                top_k=retrieval_k,
            )

        focused_queries = self._query_builder.build(
            query,
            perspectives,
        )

        merged: list[HybridSearchResult] = []
        seen_ids: set[str] = set()

        for perspective in perspectives:
            perspective_query = focused_queries[perspective]

            queries: tuple[str, ...] = (
                perspective_query
                if isinstance(perspective_query, tuple)
                else (perspective_query,)
            )

            for focused_query in queries:
                results = self._retriever.search(
                    focused_query,
                    top_k=retrieval_k,
                )

                self._append_unique(
                    merged=merged,
                    seen_ids=seen_ids,
                    results=results,
                )

        return merged

    @staticmethod
    def _append_unique(
        *,
        merged: list[HybridSearchResult],
        seen_ids: set[str],
        results: list[HybridSearchResult],
    ) -> None:
        """Append retrieval results while preserving unique chunk IDs."""

        for result in results:
            if result.chunk_id in seen_ids:
                continue

            seen_ids.add(result.chunk_id)
            merged.append(result)