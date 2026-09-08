"""Orchestration service for evidence-grounded analysis."""

from __future__ import annotations

from app.domain.models.analysis import EvidenceContext
from app.modules.analysis.analyzer import EvidenceAnalyzer
from app.modules.analysis.context_builder import EvidenceContextBuilder
from app.modules.analysis.evidence_guard import EvidenceConsistencyGuard
from app.modules.retrieval.hybrid_retriever import HybridRetriever
from app.modules.retrieval.reranker import CrossEncoderReranker


class AnalysisService:
    """Run retrieval, reranking, context building, and analysis."""

    def __init__(
        self,
        *,
        retriever: HybridRetriever,
        reranker: CrossEncoderReranker,
        context_builder: EvidenceContextBuilder,
        analyzer: EvidenceAnalyzer,
        evidence_guard: EvidenceConsistencyGuard,
    ) -> None:
        self._retriever = retriever
        self._reranker = reranker
        self._context_builder = context_builder
        self._analyzer = analyzer
        self._evidence_guard = evidence_guard

    def build_context(
        self,
        *,
        query: str,
        retrieval_top_k: int = 50,
        rerank_top_k: int = 20,
    ) -> EvidenceContext:
        """Retrieve, rerank, build, and consistency-check the analysis context."""

        hybrid_results = self._retriever.search(
            query,
            top_k=retrieval_top_k,
        )

        if not hybrid_results:
            return self._context_builder.build(
                query=query,
                reranked_results=[],
            )

        reranked_results = self._reranker.rerank(
            query=query,
            candidates=hybrid_results,
            chunk_texts=self._resolve_chunk_texts(hybrid_results),
            top_k=rerank_top_k,
        )

        context = self._context_builder.build(
            query=query,
            reranked_results=reranked_results,
        )

        guard_result = self._evidence_guard.filter(
            query=query,
            evidence=context.evidence,
        )

        filtered_evidence = (
            guard_result.direct_evidence
            + guard_result.contextual_evidence
        )

        return EvidenceContext(
            query=context.query,
            evidence=filtered_evidence,
            direct_evidence_ids=tuple(
                evidence.evidence_id
                for evidence in guard_result.direct_evidence
            ),
            contextual_evidence_ids=tuple(
                evidence.evidence_id
                for evidence in guard_result.contextual_evidence
            ),
        )

    def analyze(
        self,
        *,
        query: str,
        retrieval_top_k: int = 50,
        rerank_top_k: int = 20,
    ):
        """Run the complete retrieval-to-analysis pipeline."""

        context = self.build_context(
            query=query,
            retrieval_top_k=retrieval_top_k,
            rerank_top_k=rerank_top_k,
        )

        return self._analyzer.analyze(
            context=context,
        )

    def _resolve_chunk_texts(self, results) -> dict[str, str]:
        """Resolve chunk IDs to text for cross-encoder reranking."""

        from app.repositories.chunk_file_store import get_chunks_by_id

        chunks = get_chunks_by_id(
            [result.chunk_id for result in results],
            chunk_store_dir=self._context_builder.chunk_store_dir,
        )

        return {
            chunk_id: chunk.text
            for chunk_id, chunk in chunks.items()
        }