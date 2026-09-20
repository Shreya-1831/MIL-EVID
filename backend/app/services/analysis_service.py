"""Fast orchestration service for evidence-grounded analysis (OPTIMIZED)."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import UUID

from app.domain.enums import Perspective
from app.domain.models.analysis import (
    Citation,
    EvidenceContext,
    FinalAnalysisResponse,
)
from app.domain.models.query import QueryClassification
from app.modules.analysis.analyzer import EvidenceAnalyzer
from app.modules.analysis.claim_verifier import ClaimVerifier
from app.modules.analysis.confidence_scorer import ConfidenceScorer
from app.modules.analysis.context_builder import EvidenceContextBuilder
from app.modules.analysis.contradiction_detector import ContradictionDetector
from app.modules.analysis.evidence_guard import EvidenceConsistencyGuard
from app.modules.analysis.perspective_selector import (
    PerspectiveAwareCandidateSelector,
)
from app.modules.analysis.post_rerank_perspective_selector import (
    PostRerankPerspectiveSelector,
)
from app.modules.retrieval.acled_retriever import ACLEDDynamicRetriever
from app.modules.retrieval.perspective_retriever import PerspectiveAwareRetriever
from app.modules.retrieval.reranker import CrossEncoderReranker
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.chunk_file_store import get_chunks_by_id

logger = logging.getLogger("mil_evid")


class AnalysisService:
    """Run retrieval, reranking, evidence filtering, and analysis."""

    def __init__(
        self,
        *,
        perspective_retriever: PerspectiveAwareRetriever,
        acled_retriever: ACLEDDynamicRetriever | None = None,
        reranker: CrossEncoderReranker,
        perspective_selector: PerspectiveAwareCandidateSelector,
        post_rerank_perspective_selector: PostRerankPerspectiveSelector,
        context_builder: EvidenceContextBuilder,
        analyzer: EvidenceAnalyzer,
        evidence_guard: EvidenceConsistencyGuard,
        contradiction_detector: ContradictionDetector,
        confidence_scorer: ConfidenceScorer,
        claim_verifier: ClaimVerifier,
        rerank_candidate_k: int = 10,
        skip_claim_verification: bool = False,
    ) -> None:
        self._perspective_retriever = perspective_retriever
        self._acled_retriever = acled_retriever
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
        self._rerank_candidate_k = max(1, rerank_candidate_k)
        self._skip_claim_verification = skip_claim_verification

    def build_context(
        self,
        *,
        query: str,
        retrieval_top_k: int = 50,  # OPTIMIZED: Reduced from 100
        rerank_top_k: int = 8,
        acled_country: str | None = None,
        acled_start_date: str | None = None,
        acled_end_date: str | None = None,
        acled_updated_since: str | None = None,
    ) -> EvidenceContext:
        """Retrieve, rerank, select, and consistency-check compact evidence."""
        started = time.perf_counter()

        requested_perspectives = (
            Perspective.MILITARY,
            Perspective.LEGAL,
            Perspective.HISTORICAL,
        )

        # OPTIMIZED: Parallelize retrieval + ACLED
        retrieval_started = time.perf_counter()

        with ThreadPoolExecutor(
            max_workers=3,
            thread_name_prefix="mil-evid-retrieval",
        ) as executor:
            # Perspective retrieval
            hybrid_future = executor.submit(
                self._perspective_retriever.search,
                query=query,
                perspectives=requested_perspectives,
                top_k=retrieval_top_k,
            )

            # ACLED retrieval (parallel)
            acled_documents = []
            acled_future = None
            if self._acled_retriever is not None and acled_country:
                acled_future = executor.submit(
                    self._acled_retriever.retrieve,
                    country=acled_country,
                    start_date=acled_start_date,
                    end_date=acled_end_date,
                    updated_since=acled_updated_since,
                    limit=retrieval_top_k,
                )

            # Get perspective results
            hybrid_results = hybrid_future.result()

            # Get ACLED results if requested
            if acled_future is not None:
                acled_documents = acled_future.result()

                logger.info(
                    "========== ACLED DEBUG =========="
                )
                logger.info(
                    "country=%s start_date=%s end_date=%s updated_since=%s",
                    acled_country,
                    acled_start_date,
                    acled_end_date,
                    acled_updated_since,
                )
                logger.info(
                    "ACLED retrieved count=%d",
                    len(acled_documents),
                )

                for item in acled_documents[:10]:
                    logger.info(
                        "ACLED evidence: source=%s perspective=%s "
                        "id=%s",
                        item.source,
                        item.perspective,
                        item.evidence_id,
                    )

                logger.info(
                    "================================"
                )
            else:
                logger.info(
                    "ACLED SKIPPED: retriever=%s country=%s",
                    self._acled_retriever is not None,
                    acled_country,
                )

        retrieval_elapsed = time.perf_counter() - retrieval_started

        print("\n========== ACLED ROUTE DEBUG ==========")
        print("ACLED retriever exists:", self._acled_retriever is not None)
        print("ACLED country:", repr(acled_country))
        print("ACLED start date:", repr(acled_start_date))
        print("ACLED end date:", repr(acled_end_date))
        print("ACLED updated since:", repr(acled_updated_since))
        print("=======================================\n")

        logger.info(
            "RAW HYBRID RESULTS: count=%d ids=%s",
            len(hybrid_results),
            [result.chunk_id for result in hybrid_results],
        )

        if not hybrid_results:
            return self._context_builder.build(
                query=query,
                reranked_results=[],
            )

        selection_started = time.perf_counter()

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

        selection_elapsed = time.perf_counter() - selection_started

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

        context_started = time.perf_counter()

        context = self._context_builder.build(
            query=query,
            reranked_results=reranked_results,
        )

        context_elapsed = time.perf_counter() - context_started

        dynamic_evidence = ()
        acled_rerank_elapsed = 0.0

        # OPTIMIZED: Rerank ACLED results if retrieved
        if acled_documents:
            acled_rerank_started = time.perf_counter()

            acled_reranked = self._reranker.rerank_evidence(
                query=query,
                evidence=acled_documents,
                top_k=rerank_top_k,
            )

            dynamic_context = self._context_builder.build_dynamic(
                query=query,
                reranked_evidence=acled_reranked,
            )

            dynamic_evidence = dynamic_context.evidence

            acled_rerank_elapsed = time.perf_counter() - acled_rerank_started

            logger.info(
                "ACLED dynamic retrieval: country=%s updated_since=%s "
                "retrieved=%d reranked=%d",
                acled_country,
                acled_updated_since,
                len(acled_documents),
                len(dynamic_evidence),
            )

        selected_evidence = self._post_rerank_perspective_selector.select(
            query=query,
            evidence=context.evidence + dynamic_evidence,
            max_evidence=rerank_top_k,
        )

        guarded_direct = []
        guarded_contextual = []

        for perspective in (
            Perspective.MILITARY,
            Perspective.LEGAL,
            Perspective.HISTORICAL,
        ):
            if perspective == Perspective.MILITARY:
                # UCDP/ACLED are military evidence regardless of
                # their stored perspective metadata.
                perspective_evidence = tuple(
                    e
                    for e in selected_evidence
                    if e.source in {
                        "UCDP GED",
                        "UCDP Dyadic",
                        "ACLED",
                    }
                )
            else:
                perspective_evidence = tuple(
                    e
                    for e in selected_evidence
                    if e.source not in {
                        "UCDP GED",
                        "UCDP Dyadic",
                        "ACLED",
                    }
                    and e.perspective == perspective
                )

            if not perspective_evidence:
                continue

            guard_result = self._evidence_guard.filter(
                query=query,
                evidence=perspective_evidence,
                perspective=perspective.value,
            )

            guarded_direct.extend(guard_result.direct_evidence)
            guarded_contextual.extend(guard_result.contextual_evidence)

        filtered_evidence = tuple(guarded_direct)

        logger.info(
            "Pipeline timing: retrieval=%.3fs selection=%.3fs "
            "rerank=%.3fs context=%.3fs acled_rerank=%.3fs "
            "hybrid=%d candidates=%d reranked=%d selected=%d "
            "direct=%d contextual=%d",
            retrieval_elapsed,
            selection_elapsed,
            rerank_elapsed,
            context_elapsed,
            acled_rerank_elapsed,
            len(hybrid_results),
            len(candidate_results),
            len(reranked_results),
            len(filtered_evidence),
            # len(direct_evidence),
            # len(contextual_evidence),
        )
        return EvidenceContext(
            query=context.query,
            evidence=filtered_evidence,
            direct_evidence_ids=tuple(
                e.evidence_id
                for e in guarded_direct
            ),
            contextual_evidence_ids=tuple(
                e.evidence_id
                for e in guarded_contextual
            ),
        )


    def analyze(
        self,
        *,
        user_id: UUID,
        query: str,
        analysis_repository: AnalysisRepository,
        retrieval_top_k: int = 50,  # OPTIMIZED: Reduced from 100
        rerank_top_k: int = 8,
        acled_country: str | None = None,
        acled_start_date: str | None = None,
        acled_end_date: str | None = None,
        acled_updated_since: str | None = None,
    ) -> FinalAnalysisResponse:
        """Run the complete optimized pipeline."""

        total_started = time.perf_counter()
        started_at = datetime.now(timezone.utc)

        context = self.build_context(
            query=query,
            retrieval_top_k=retrieval_top_k,
            rerank_top_k=rerank_top_k,
            acled_country=acled_country,
            acled_updated_since=acled_updated_since,
            acled_start_date=acled_start_date,
            acled_end_date=acled_end_date,
        )

        analysis_started = time.perf_counter()

        military, legal, historical = self._analyzer.analyze(
            context=context,
        )

        analysis_elapsed = time.perf_counter() - analysis_started

        claims = self._deduplicate_claims(
            military.claims + legal.claims + historical.claims
        )

        # OPTIMIZED: Conditionally skip claim verification
        if self._skip_claim_verification:
            # Claim verification is intentionally skipped for performance.
            # FinalAnalysisResponse expects a tuple, not None.
            claim_verification = ()
            verification_elapsed = 0.0

            # Run only contradiction detection
            contradiction_started = time.perf_counter()

            contradictions = self._contradiction_detector.detect(
                evidence=context.evidence,
            )

            contradiction_elapsed = (
                time.perf_counter() - contradiction_started
            )

        else:
            # Run both verification and contradiction in parallel
            verification_started = time.perf_counter()

            with ThreadPoolExecutor(
                max_workers=3,
                thread_name_prefix="mil-evid-post-analysis",
            ) as executor:
                verification_future = executor.submit(
                    self._claim_verifier.verify,
                    claims=claims,
                    evidence=context.evidence,
                )

                contradiction_future = executor.submit(
                    self._contradiction_detector.detect,
                    evidence=context.evidence,
                )

                claim_verification = verification_future.result()
                contradictions = contradiction_future.result()

            verification_elapsed = time.perf_counter() - verification_started
            contradiction_elapsed = verification_elapsed  # Both ran in parallel

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

        total_elapsed = time.perf_counter() - total_started

        logger.info(
            "OPTIMIZED PIPELINE TIMING: analysis=%.3fs "
            "verification=%.3fs contradiction=%.3fs total=%.3fs "
            "skip_verification=%s",
            analysis_elapsed,
            verification_elapsed,
            contradiction_elapsed,
            total_elapsed,
            self._skip_claim_verification,
        )

        result = FinalAnalysisResponse(
            query=query_classification,
            military_analysis=military,
            legal_analysis=legal,
            historical_analysis=historical,
            evidence=context.evidence,
            contradictions=contradictions,
            claim_verification=claim_verification,
            confidence=confidence,
            citations=citations,
        )

        completed_at = datetime.now(timezone.utc)

        try:
            analysis_repository.create_analysis(
                user_id=user_id,
                query_text=query,
                result=result,
                evidence=context.evidence,
                started_at=started_at,
                completed_at=completed_at,
            )
        except Exception:
            logger.exception(
                "Failed to persist analysis result for user=%s",
                user_id,
            )
            raise

        return result

    @staticmethod
    def _deduplicate_claims(
        claims: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Remove duplicate claims (normalized)."""
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
        """Collect unique citations from all perspectives."""
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
        """Resolve chunk IDs to their full text."""
        chunks = get_chunks_by_id(
            [result.chunk_id for result in results],
            chunk_store_dir=self._context_builder.chunk_store_dir,
        )

        return {
            chunk_id: chunk.text
            for chunk_id, chunk in chunks.items()
        }

    @staticmethod
    def _evidence_matches_perspective(
        *,
        evidence,
        perspective: Perspective,
    ) -> bool:
        """Check if evidence is relevant to a perspective."""
        if evidence.source in {"UCDP GED", "UCDP Dyadic"}:
            return perspective == Perspective.MILITARY

        if evidence.perspective is not None:
            return evidence.perspective == perspective

        return False