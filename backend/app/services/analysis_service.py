"""Fast orchestration service for evidence-grounded analysis."""

from __future__ import annotations

import logging
import time

from app.domain.enums import Perspective
from app.domain.models.analysis import Citation, EvidenceContext, FinalAnalysisResponse
from app.domain.models.query import QueryClassification
from app.modules.analysis.analyzer import EvidenceAnalyzer
from app.modules.analysis.claim_verifier import ClaimVerifier
from app.modules.analysis.confidence_scorer import ConfidenceScorer
from app.modules.analysis.context_builder import EvidenceContextBuilder
from app.modules.analysis.contradiction_detector import ContradictionDetector
from app.modules.analysis.evidence_guard import EvidenceConsistencyGuard
from app.modules.analysis.perspective_selector import PerspectiveAwareCandidateSelector
from app.modules.analysis.post_rerank_perspective_selector import PostRerankPerspectiveSelector
from app.modules.retrieval.perspective_retriever import PerspectiveAwareRetriever
from app.modules.retrieval.reranker import CrossEncoderReranker
from app.repositories.chunk_file_store import get_chunks_by_id

logger = logging.getLogger("mil_evid")


class AnalysisService:
    """Run retrieval, reranking, evidence filtering, and analysis."""

    def __init__(
        self,
        *,
        perspective_retriever: PerspectiveAwareRetriever,
        reranker: CrossEncoderReranker,
        perspective_selector: PerspectiveAwareCandidateSelector,
        post_rerank_perspective_selector: PostRerankPerspectiveSelector,
        context_builder: EvidenceContextBuilder,
        analyzer: EvidenceAnalyzer,
        evidence_guard: EvidenceConsistencyGuard,
        contradiction_detector: ContradictionDetector,
        confidence_scorer: ConfidenceScorer,
        claim_verifier: ClaimVerifier,
        rerank_candidate_k: int = 15,
    ) -> None:
        self._perspective_retriever = perspective_retriever
        self._reranker = reranker
        self._context_builder = context_builder
        self._analyzer = analyzer
        self._evidence_guard = evidence_guard
        self._perspective_selector = perspective_selector
        self._post_rerank_perspective_selector = post_rerank_perspective_selector
        self._contradiction_detector = contradiction_detector
        self._confidence_scorer = confidence_scorer
        self._claim_verifier = claim_verifier
        self._rerank_candidate_k = max(1, rerank_candidate_k)

    def build_context(
        self,
        *,
        query: str,
        retrieval_top_k: int = 15,
        rerank_top_k: int = 4,
    ) -> EvidenceContext:
        """Retrieve, rerank, select, and consistency-check compact evidence."""
        started = time.perf_counter()

        requested_perspectives = (
            Perspective.MILITARY,
            Perspective.LEGAL,
            Perspective.HISTORICAL,
        )

        hybrid_results = self._perspective_retriever.search(
            query=query,
            perspectives=requested_perspectives,
            top_k=retrieval_top_k,
        )

        retrieval_elapsed = time.perf_counter() - started

        if not hybrid_results:
            return self._context_builder.build(
                query=query,
                reranked_results=[],
            )

        evidence_by_id = get_chunks_by_id(
            [result.chunk_id for result in hybrid_results],
            chunk_store_dir=self._context_builder.chunk_store_dir,
        )

        selection = self._perspective_selector.select(
            query=query,
            candidates=hybrid_results,
            evidence_by_id=evidence_by_id,
        )
        candidate_results = selection.candidates

        logger.info(
            "Perspective candidates: requested=%s sources=%s",
            selection.requested_perspectives,
            [
                (
                    evidence_by_id[candidate.chunk_id].source,
                    evidence_by_id[candidate.chunk_id].perspective,
                    candidate.chunk_id,
                )
                for candidate in candidate_results
                if candidate.chunk_id in evidence_by_id
            ],
        )

        rerank_candidates = candidate_results[: self._rerank_candidate_k]

        rerank_started = time.perf_counter()

        reranked_results = self._reranker.rerank(
            query=query,
            candidates=rerank_candidates,
            chunk_texts=self._resolve_chunk_texts(rerank_candidates),
            top_k=len(rerank_candidates),
        )

        rerank_elapsed = time.perf_counter() - rerank_started

        context = self._context_builder.build(
            query=query,
            reranked_results=reranked_results,
        )

        selected_evidence = self._post_rerank_perspective_selector.select(
            query=query,
            evidence=context.evidence,
            max_evidence=rerank_top_k,
        )

        guard_result = self._evidence_guard.filter(
            query=query,
            evidence=selected_evidence,
        )

        filtered_evidence = (
            guard_result.direct_evidence + guard_result.contextual_evidence
        )

        direct_ids = {
            evidence.evidence_id
            for evidence in guard_result.direct_evidence
        }

        direct_evidence = tuple(
            evidence
            for evidence in filtered_evidence
            if evidence.evidence_id in direct_ids
        )

        contextual_evidence = tuple(
            evidence
            for evidence in filtered_evidence
            if evidence.evidence_id not in direct_ids
        )

        logger.info(
            "Pipeline retrieval=%.3fs rerank=%.3fs hybrid=%d "
            "candidates=%d reranked=%d selected=%d direct=%d contextual=%d",
            retrieval_elapsed,
            rerank_elapsed,
            len(hybrid_results),
            len(candidate_results),
            len(reranked_results),
            len(filtered_evidence),
            len(direct_evidence),
            len(contextual_evidence),
        )

        return EvidenceContext(
            query=context.query,
            evidence=filtered_evidence,
            direct_evidence_ids=tuple(
                evidence.evidence_id
                for evidence in direct_evidence
            ),
            contextual_evidence_ids=tuple(
                evidence.evidence_id
                for evidence in contextual_evidence
            ),
        )

    def analyze(
        self,
        *,
        query: str,
        retrieval_top_k: int = 15,
        rerank_top_k: int = 4,
    ) -> FinalAnalysisResponse:
        """Run the complete optimized pipeline."""
        total_started = time.perf_counter()

        context = self.build_context(
            query=query,
            retrieval_top_k=retrieval_top_k,
            rerank_top_k=rerank_top_k,
        )

        analysis_started = time.perf_counter()

        military, legal, historical = self._analyzer.analyze(
            context=context,
        )

        analysis_elapsed = time.perf_counter() - analysis_started

        claims = self._deduplicate_claims(
            military.claims + legal.claims + historical.claims
        )

        verification_started = time.perf_counter()

        claim_verification = self._claim_verifier.verify(
            claims=claims,
            evidence=context.evidence,
        )

        verification_elapsed = time.perf_counter() - verification_started

        contradiction_started = time.perf_counter()

        contradictions = self._contradiction_detector.detect(
            evidence=context.evidence,
        )

        contradiction_elapsed = time.perf_counter() - contradiction_started

        confidence = self._confidence_scorer.score(
            evidence=context.evidence,
            contradictions=contradictions,
            claim_verification=claim_verification,
        )

        query_classification = QueryClassification(
            raw_query=query,
            normalized_query=query.strip(),
        )

        citations = self._collect_citations(
            military=military,
            legal=legal,
            historical=historical,
        )

        logger.info(
            "Pipeline timing: analysis=%.3fs verification=%.3fs "
            "contradiction=%.3fs total=%.3fs",
            analysis_elapsed,
            verification_elapsed,
            contradiction_elapsed,
            time.perf_counter() - total_started,
        )

        return FinalAnalysisResponse(
            query=query_classification,
            military_analysis=military,
            legal_analysis=legal,
            historical_analysis=historical,
            contradictions=contradictions,
            claim_verification=claim_verification,
            confidence=confidence,
            citations=citations,
        )

    @staticmethod
    def _deduplicate_claims(
        claims: tuple[str, ...],
    ) -> tuple[str, ...]:
        seen: set[str] = set()
        unique_claims: list[str] = []

        for claim in claims:
            normalized = " ".join(
                claim.strip().lower().split()
            )

            if not normalized or normalized in seen:
                continue

            seen.add(normalized)
            unique_claims.append(claim.strip())

        return tuple(unique_claims)

    @staticmethod
    def _collect_citations(
        *,
        military,
        legal,
        historical,
    ) -> tuple[Citation, ...]:
        citations: list[Citation] = []
        seen: set[str] = set()

        for result in (military, legal, historical):
            for citation in result.citations:
                if citation.evidence_id in seen:
                    continue

                seen.add(citation.evidence_id)
                citations.append(citation)

        return tuple(citations)

    def _resolve_chunk_texts(
        self,
        results,
    ) -> dict[str, str]:
        chunks = get_chunks_by_id(
            [result.chunk_id for result in results],
            chunk_store_dir=self._context_builder.chunk_store_dir,
        )

        return {
            chunk_id: chunk.text
            for chunk_id, chunk in chunks.items()
        }