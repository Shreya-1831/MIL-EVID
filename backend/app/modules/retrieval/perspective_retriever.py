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
        top_k_per_perspective: int = 20,
    ) -> None:
        self._retriever = retriever
        self._query_builder = query_builder
        self._top_k_per_perspective = max(1, top_k_per_perspective)

    def search(
        self,
        *,
        query: str,
        perspectives: tuple[Perspective, ...],
        top_k: int | None = None,
    ) -> list[HybridSearchResult]:
        """Retrieve and merge candidates across perspectives."""
        if not perspectives:
            return self._retriever.search(
                query,
                top_k=self._top_k_per_perspective,
            )

        focused_queries = self._query_builder.build(
            query,
            perspectives,
        )

        merged: list[HybridSearchResult] = []
        seen_ids: set[str] = set()

        for perspective in perspectives:
            results = self._retriever.search(
                focused_queries[perspective],
                top_k=self._top_k_per_perspective,
            )

            for result in results:
                if result.chunk_id in seen_ids:
                    continue

                seen_ids.add(result.chunk_id)
                merged.append(result)

        return merged