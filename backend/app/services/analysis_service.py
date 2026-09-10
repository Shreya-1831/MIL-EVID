"""Orchestration service for evidence-grounded analysis."""

from __future__ import annotations

from app.domain.models.analysis import (
    Citation,
    EvidenceContext,
    FinalAnalysisResponse,
)
from app.modules.analysis.perspective_selector import (
    PerspectiveAwareCandidateSelector,
)
from app.domain.models.query import QueryClassification
from app.modules.analysis.analyzer import EvidenceAnalyzer
from app.modules.analysis.claim_verifier import ClaimVerifier
from app.modules.analysis.confidence_scorer import ConfidenceScorer
from app.modules.analysis.context_builder import EvidenceContextBuilder
from app.modules.analysis.contradiction_detector import (
    ContradictionDetector,
)
from app.modules.analysis.evidence_guard import EvidenceConsistencyGuard
from app.modules.retrieval.hybrid_retriever import HybridRetriever
from app.modules.retrieval.reranker import CrossEncoderReranker
from app.modules.analysis.post_rerank_perspective_selector import (
    PostRerankPerspectiveSelector,
)


class AnalysisService:
    """Run retrieval, analysis, verification, and response assembly."""

    # Limit the amount of evidence passed to the LLM and
    # contradiction detector after reranking and consistency filtering.
    # MAX_ANALYSIS_EVIDENCE = 6

    def __init__(
        self,
        *,
        retriever: HybridRetriever,
        reranker: CrossEncoderReranker,
        perspective_selector: PerspectiveAwareCandidateSelector,
        post_rerank_perspective_selector: PostRerankPerspectiveSelector,
        context_builder: EvidenceContextBuilder,
        analyzer: EvidenceAnalyzer,
        evidence_guard: EvidenceConsistencyGuard,
        contradiction_detector: ContradictionDetector,
        confidence_scorer: ConfidenceScorer,
        claim_verifier: ClaimVerifier,
    ) -> None:
        self._retriever = retriever
        self._reranker = reranker
        self._context_builder = context_builder
        self._analyzer = analyzer
        self._evidence_guard = evidence_guard
        self._perspective_selector = perspective_selector
        self._post_rerank_perspective_selector = (
            post_rerank_perspective_selector
        )
        self._contradiction_detector = contradiction_detector
        self._confidence_scorer = confidence_scorer
        self._claim_verifier = claim_verifier

    def build_context(
        self,
        *,
        query: str,
        retrieval_top_k: int = 50,
        rerank_top_k: int = 20,
    ) -> EvidenceContext:
        """Retrieve, rerank, build, and consistency-check the analysis context."""

        # ================================================================
        # STEP 1: HYBRID RETRIEVAL
        # ================================================================

        hybrid_results = self._retriever.search(
            query,
            top_k=retrieval_top_k,
        )

        if not hybrid_results:
            return self._context_builder.build(
                query=query,
                reranked_results=[],
            )

        # ================================================================
        # STEP 2: PERSPECTIVE-AWARE CANDIDATE PRESERVATION
        # ================================================================

        selection = self._perspective_selector.select(
            query=query,
            candidates=hybrid_results,
        )

        candidate_results = selection.candidates

        # ================================================================
        # STEP 3: CROSS-ENCODER RERANKING
        #
        # IMPORTANT:
        # The cross-encoder scores ALL preserved candidates.
        # We deliberately do NOT use rerank_top_k here.
        # ================================================================

        reranked_results = self._reranker.rerank(
            query=query,
            candidates=candidate_results,
            chunk_texts=self._resolve_chunk_texts(candidate_results),
            top_k=len(candidate_results),
        )

        # ================================================================
        # STEP 4: BUILD EVIDENCE CONTEXT
        # ================================================================

        context = self._context_builder.build(
            query=query,
            reranked_results=reranked_results,
        )

        # ================================================================
        # STEP 5: POST-RERANK PERSPECTIVE-AWARE SELECTION
        #
        # This is where rerank_top_k currently acts as the final
        # evidence budget.
        #
        # The selector calculates source proportions from the actual
        # retrieved evidence. No fixed source quotas are imposed.
        # ================================================================

        selected_evidence = (
            self._post_rerank_perspective_selector.select(
                query=query,
                evidence=context.evidence,
                max_evidence=rerank_top_k,
            )
        )

        # ================================================================
        # TEMPORARY DEBUG #1
        #
        # This tells us exactly what survived the proportional
        # post-reranking selector.
        # ================================================================

        print("\n========== POST-RERANK EVIDENCE DEBUG ==========")
        print(
            f"Input evidence count: "
            f"{len(context.evidence)}"
        )
        print(
            f"Selected evidence count: "
            f"{len(selected_evidence)}"
        )

        for index, evidence in enumerate(
            selected_evidence,
            start=1,
        ):
            print(
                f"{index}. "
                f"source={evidence.source!r}, "
                f"score={evidence.reranker_score:.4f}, "
                f"id={evidence.evidence_id}"
            )

        print("===============================================\n")

        print("\n========== SELECTED EVIDENCE TEXT DEBUG ==========")

        for index, evidence in enumerate(
            selected_evidence,
            start=1,
        ):
            preview = " ".join(
                evidence.text.strip().split()
            )

            if len(preview) > 500:
                preview = preview[:500] + "..."

            print(
                f"\n{index}. "
                f"source={evidence.source!r}\n"
                f"score={evidence.reranker_score:.4f}\n"
                f"id={evidence.evidence_id}\n"
                f"text={preview}"
            )

        print("===================================================\n")

        # ================================================================
        # STEP 6: EVIDENCE CONSISTENCY GUARD
        # ================================================================

        guard_result = self._evidence_guard.filter(
            query=query,
            evidence=selected_evidence,
        )

        # Preserve both direct and contextual evidence.
        filtered_evidence = (
            guard_result.direct_evidence
            + guard_result.contextual_evidence
        )

        # ================================================================
        # TEMPORARY DEBUG #2
        #
        # This tells us whether the EvidenceConsistencyGuard is
        # actually removing evidence or simply classifying it.
        # ================================================================

        print("\n========== AFTER EVIDENCE GUARD DEBUG ==========")
        print(
            f"Final evidence count: "
            f"{len(filtered_evidence)}"
        )
        print(
            f"Direct evidence count: "
            f"{len(guard_result.direct_evidence)}"
        )
        print(
            f"Contextual evidence count: "
            f"{len(guard_result.contextual_evidence)}"
        )

        direct_ids = {
            evidence.evidence_id
            for evidence in guard_result.direct_evidence
        }

        for index, evidence in enumerate(
            filtered_evidence,
            start=1,
        ):
            classification = (
                "DIRECT"
                if evidence.evidence_id in direct_ids
                else "CONTEXTUAL"
            )

            print(
                f"{index}. "
                f"[{classification}] "
                f"source={evidence.source!r}, "
                f"score={evidence.reranker_score:.4f}, "
                f"id={evidence.evidence_id}"
            )

        print("================================================\n")

        # ================================================================
        # STEP 7: FINAL EVIDENCE LIMIT
        #
        # Intentionally disabled for now.
        #
        # We first need to measure whether the post-rerank selector
        # already gives us an appropriate evidence set.
        # ================================================================

        # filtered_evidence = filtered_evidence[
        #     : self.MAX_ANALYSIS_EVIDENCE
        # ]

        # ================================================================
        # STEP 8: PRESERVE DIRECT / CONTEXTUAL CLASSIFICATION
        # ================================================================

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

        # ================================================================
        # STEP 9: RETURN FINAL CONTEXT
        # ================================================================

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
        retrieval_top_k: int = 50,
        rerank_top_k: int = 20,
    ) -> FinalAnalysisResponse:
        """Run the complete pipeline and assemble the final response."""

        # ================================================================
        # RETRIEVAL → RERANKING → EVIDENCE GROUNDING
        # ================================================================

        context = self.build_context(
            query=query,
            retrieval_top_k=retrieval_top_k,
            rerank_top_k=rerank_top_k,
        )

        # ================================================================
        # MULTI-PERSPECTIVE LLM ANALYSIS
        # ================================================================

        military, legal, historical = self._analyzer.analyze(
            context=context,
        )

        # ================================================================
        # CLAIM VERIFICATION
        # ================================================================

        claims = self._deduplicate_claims(
            military.claims
            + legal.claims
            + historical.claims
        )

        claim_verification = self._claim_verifier.verify(
            claims=claims,
            evidence=context.evidence,
        )

        # ================================================================
        # CONTRADICTION DETECTION
        # ================================================================

        contradictions = self._contradiction_detector.detect(
            evidence=context.evidence,
        )

        # ================================================================
        # CONFIDENCE SCORING
        # ================================================================

        confidence = self._confidence_scorer.score(
            evidence=context.evidence,
            contradictions=contradictions,
            claim_verification=claim_verification,
        )

        # ================================================================
        # BASIC QUERY CLASSIFICATION
        # ================================================================

        query_classification = QueryClassification(
            raw_query=query,
            normalized_query=query.strip(),
        )

        # ================================================================
        # COLLECT AND DEDUPLICATE CITATIONS
        # ================================================================

        citations = self._collect_citations(
            military=military,
            legal=legal,
            historical=historical,
        )

        # ================================================================
        # FINAL RESPONSE
        # ================================================================

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
        """Remove duplicate claims while preserving their original order."""

        seen: set[str] = set()
        unique_claims: list[str] = []

        for claim in claims:
            normalized = " ".join(
                claim.strip().lower().split()
            )

            if not normalized:
                continue

            if normalized in seen:
                continue

            seen.add(normalized)
            unique_claims.append(
                claim.strip()
            )

        return tuple(unique_claims)

    @staticmethod
    def _collect_citations(
        *,
        military,
        legal,
        historical,
    ) -> tuple[Citation, ...]:
        """Collect and deduplicate citations from all perspectives."""

        citations: list[Citation] = []
        seen: set[str] = set()

        for result in (
            military,
            legal,
            historical,
        ):
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
        """Resolve chunk IDs to text for cross-encoder reranking."""

        from app.repositories.chunk_file_store import (
            get_chunks_by_id,
        )

        chunks = get_chunks_by_id(
            [
                result.chunk_id
                for result in results
            ],
            chunk_store_dir=(
                self._context_builder.chunk_store_dir
            ),
        )

        return {
            chunk_id: chunk.text
            for chunk_id, chunk in chunks.items()
        }