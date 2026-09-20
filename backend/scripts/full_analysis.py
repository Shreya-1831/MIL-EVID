"""Run the optimized MIL-EVID retrieval and analysis pipeline."""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv

from app.core.config import get_settings
from app.database.session import get_session_factory
from app.modules.analysis.analyzer import EvidenceAnalyzer
from app.modules.analysis.claim_verifier import ClaimVerifier
from app.modules.analysis.confidence_scorer import ConfidenceScorer
from app.modules.analysis.context_builder import EvidenceContextBuilder
from app.modules.analysis.contradiction_detector import (
    ContradictionDetector,
)
from app.modules.analysis.evidence_guard import EvidenceConsistencyGuard
from app.modules.analysis.llm_client import OllamaClient
from app.modules.analysis.perspective_selector import (
    PerspectiveAwareCandidateSelector,
)
from app.modules.analysis.post_rerank_perspective_selector import (
    PostRerankPerspectiveSelector,
)
from app.modules.ingestion.acled_client import ACLEDClient
from app.modules.retrieval.acled_retriever import ACLEDDynamicRetriever
from app.modules.retrieval.country_resolver import resolve_country
from app.modules.retrieval.hybrid_retriever import HybridRetriever
from app.modules.retrieval.perspective_query_builder import (
    PerspectiveQueryBuilder,
)
from app.modules.retrieval.perspective_retriever import (
    PerspectiveAwareRetriever,
)
from app.modules.retrieval.reranker import CrossEncoderReranker
from app.repositories.analysis_repository import AnalysisRepository
from app.services.analysis_service import AnalysisService


def main() -> None:
    load_dotenv()
    settings = get_settings()

    print("=" * 80)
    print("MIL-EVID — OPTIMIZED FULL ANALYSIS PIPELINE")
    print("=" * 80)

    query = input(
        "\nEnter your military situation query:\n> "
    ).strip()

    if not query:
        print("Query cannot be empty.")
        return

    started = time.perf_counter()

    # ------------------------------------------------------------------
    # 1. Load retrieval indexes
    # ------------------------------------------------------------------
    print("\n[1/5] Loading retrieval indexes...")

    retriever = HybridRetriever.from_index_dirs(
        bm25_index_dir=Path(settings.bm25_index_dir),
        faiss_index_dir=Path(settings.faiss_index_dir),
        rrf_k=settings.rrf_k,
    )

    perspective_retriever = PerspectiveAwareRetriever(
        retriever=retriever,
        query_builder=PerspectiveQueryBuilder(),
    )

    # ------------------------------------------------------------------
    # 2. Load cross-encoder reranker
    # ------------------------------------------------------------------
    print("[2/5] Loading cross-encoder reranker...")

    reranker = CrossEncoderReranker(
        model_name=settings.reranker_model,
    )

    # ------------------------------------------------------------------
    # 3. Initialize analysis components
    # ------------------------------------------------------------------
    print("[3/5] Initializing evidence context and Ollama...")

    context_builder = EvidenceContextBuilder(
        chunk_store_dir=Path(settings.chunk_store_dir),
    )

    llm_client = OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
        num_predict=settings.ollama_num_predict,
        keep_alive=settings.ollama_keep_alive,
    )

    analyzer = EvidenceAnalyzer(
        llm_client=llm_client,
    )

    evidence_guard = EvidenceConsistencyGuard()

    contradiction_detector = ContradictionDetector(
        llm_client=llm_client,
    )

    claim_verifier = ClaimVerifier(
        llm_client=llm_client,
    )

    confidence_scorer = ConfidenceScorer()

    # ------------------------------------------------------------------
    # 4. Initialize ACLED dynamic retrieval
    # ------------------------------------------------------------------
    print("[4/5] Initializing ACLED dynamic retrieval...")

    acled_client = ACLEDClient(
        username=os.environ["ACLED_USERNAME"],
        password=os.environ["ACLED_PASSWORD"],
    )

    acled_retriever = ACLEDDynamicRetriever(
        client=acled_client,
    )

    # ------------------------------------------------------------------
    # Create AnalysisService
    # ------------------------------------------------------------------
    service = AnalysisService(
        perspective_retriever=perspective_retriever,
        acled_retriever=acled_retriever,
        reranker=reranker,
        context_builder=context_builder,
        analyzer=analyzer,
        evidence_guard=evidence_guard,
        contradiction_detector=contradiction_detector,
        confidence_scorer=confidence_scorer,
        claim_verifier=claim_verifier,
        perspective_selector=PerspectiveAwareCandidateSelector(),
        post_rerank_perspective_selector=PostRerankPerspectiveSelector(),
        rerank_candidate_k=settings.rerank_candidate_k,
    )

    # ------------------------------------------------------------------
    # Resolve ACLED country and update window
    # ------------------------------------------------------------------
    acled_country = resolve_country(
        query,
        settings.primary_countries,
    )

    acled_updated_since = (
        datetime.now(timezone.utc) - timedelta(days=30)
    ).isoformat()
    # acled_updated_since = None

    if acled_country:
        print(
            f"ACLED country detected: {acled_country} "
            f"(updated since: {acled_updated_since})"
        )
    else:
        print("ACLED: no primary country detected in query.")

    # ------------------------------------------------------------------
    # Resolve CLI user
    # ------------------------------------------------------------------
    cli_user_id_raw = os.getenv("MIL_EVID_CLI_USER_ID")

    if not cli_user_id_raw:
        raise RuntimeError(
            "MIL_EVID_CLI_USER_ID environment variable is required "
            "for standalone analysis execution."
        )

    try:
        cli_user_id = UUID(cli_user_id_raw)
    except ValueError as exc:
        raise RuntimeError(
            "MIL_EVID_CLI_USER_ID must be a valid UUID."
        ) from exc

    # ------------------------------------------------------------------
    # Create database session and repository
    # ------------------------------------------------------------------
    session = get_session_factory()()

    try:
        analysis_repository = AnalysisRepository(session)

        # --------------------------------------------------------------
        # 5. Run optimized analysis
        # --------------------------------------------------------------
        print("[5/5] Running optimized analysis...")

        result = service.analyze(
            user_id=cli_user_id,
            query=query,
            analysis_repository=analysis_repository,
            retrieval_top_k=settings.bm25_top_k,
            rerank_top_k=settings.rerank_top_n,
            acled_country=acled_country,
            acled_updated_since=acled_updated_since,
        )

    finally:
        session.close()

    # ------------------------------------------------------------------
    # Military Analysis
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("MILITARY ANALYSIS")
    print("=" * 80)

    print(result.military_analysis.analysis_text)

    # ------------------------------------------------------------------
    # Legal Analysis
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("LEGAL ANALYSIS")
    print("=" * 80)

    print(result.legal_analysis.analysis_text)

    # ------------------------------------------------------------------
    # Historical Analysis
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("HISTORICAL ANALYSIS")
    print("=" * 80)

    print(result.historical_analysis.analysis_text)

    # ------------------------------------------------------------------
    # Claim Verification
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("CLAIM VERIFICATION")
    print("=" * 80)

    if result.claim_verification:
        for claim in result.claim_verification:
            print(f"- Claim: {claim.claim}")
            print(
                f"  Status: {claim.status.value.upper()}"
            )
            print(
                f"  Support score: {claim.support_score:.2f}"
            )
            print(
                f"  Verified: {claim.verified}"
            )

            print(
                "  Supporting evidence: "
                + (
                    ", ".join(
                        claim.supporting_evidence_ids
                    )
                    if claim.supporting_evidence_ids
                    else "None"
                )
            )
    else:
        print("No claims were generated for verification.")

    # ------------------------------------------------------------------
    # Contradictions
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("CONTRADICTIONS")
    print("=" * 80)

    if result.contradictions:
        for contradiction in result.contradictions:
            print(
                f"- {contradiction.evidence_a_id} vs "
                f"{contradiction.evidence_b_id}: "
                f"{contradiction.status.value} "
                f"({contradiction.contradiction_type.value})"
            )

            print(
                f"  {contradiction.explanation}"
            )
    else:
        print("No contradictions detected.")

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("CONFIDENCE")
    print("=" * 80)

    print(
        f"Final score: "
        f"{result.confidence.final_score:.2f}/100"
    )

    print(
        "Confidence level: "
        f"{result.confidence.confidence_level.value.upper()}"
    )

    print(
        f"Relevance: "
        f"{result.confidence.relevance_score:.2f}"
    )

    print(
        f"Agreement: "
        f"{result.confidence.agreement_score:.2f}"
    )

    print(
        f"Freshness: "
        f"{result.confidence.freshness_score:.2f}"
    )

    print(
        "Source reliability: "
        f"{result.confidence.source_reliability_score:.2f}"
    )

    print(
        f"Claim support: "
        f"{result.confidence.claim_support_score:.2f}"
    )

    # ------------------------------------------------------------------
    # Citations
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("CITATIONS")
    print("=" * 80)

    if result.citations:
        for citation in result.citations:
            print(
                f"- {citation.evidence_id}: "
                f"{citation.source}"
            )

            if citation.title:
                print(
                    f"  Title: {citation.title}"
                )

            if citation.url:
                print(
                    f"  URL: {citation.url}"
                )
    else:
        print("No citations available.")

    # ------------------------------------------------------------------
    # Completion
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print(
        "ANALYSIS COMPLETE — total wall time: "
        f"{time.perf_counter() - started:.2f}s"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()