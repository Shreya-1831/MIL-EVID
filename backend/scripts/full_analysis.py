"""Run the complete MIL-EVID retrieval and analysis pipeline."""

from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.modules.analysis.analyzer import EvidenceAnalyzer
from app.modules.analysis.claim_verifier import ClaimVerifier
from app.modules.analysis.confidence_scorer import ConfidenceScorer
from app.modules.analysis.context_builder import EvidenceContextBuilder
from app.modules.analysis.contradiction_detector import (
    ContradictionDetector,
)
from app.modules.analysis.evidence_guard import EvidenceConsistencyGuard
from app.modules.analysis.llm_client import OllamaClient
from app.modules.retrieval.hybrid_retriever import HybridRetriever
from app.modules.retrieval.reranker import CrossEncoderReranker
from app.services.analysis_service import AnalysisService
from app.modules.analysis.perspective_selector import (
    PerspectiveAwareCandidateSelector,
)
from app.modules.analysis.post_rerank_perspective_selector import (
    PostRerankPerspectiveSelector,
)

def main() -> None:
    settings = get_settings()

    print("=" * 80)
    print("MIL-EVID — FULL ANALYSIS PIPELINE")
    print("=" * 80)

    query = input(
        "\nEnter your military situation query:\n> "
    ).strip()

    if not query:
        print("Query cannot be empty.")
        return

    print("\n[1/4] Loading retrieval indexes...")

    retriever = HybridRetriever.from_index_dirs(
        bm25_index_dir=Path(settings.bm25_index_dir),
        faiss_index_dir=Path(settings.faiss_index_dir),
        rrf_k=settings.rrf_k,
    )

    print("[2/4] Loading cross-encoder reranker...")

    reranker = CrossEncoderReranker(
        model_name=settings.reranker_model,
    )

    print("[3/4] Initializing evidence context and Llama 3.2 3B...")
    # print("[3/4] Initializing evidence context and Llama 3.1 8B...")

    context_builder = EvidenceContextBuilder(
        chunk_store_dir=Path(settings.chunk_store_dir),
    )

    # One shared LangChain/Ollama client is used by all LLM-based stages.
    llm_client = OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )

    analyzer = EvidenceAnalyzer(
        llm_client=llm_client,
    )

    evidence_guard = EvidenceConsistencyGuard()

    contradiction_detector = ContradictionDetector(
        llm_client=llm_client,
    )

    # Batch claim verification uses the same Llama client.
    claim_verifier = ClaimVerifier(
        llm_client=llm_client,
    )

    confidence_scorer = ConfidenceScorer()

    service = AnalysisService(
        retriever=retriever,
        reranker=reranker,
        context_builder=context_builder,
        analyzer=analyzer,
        evidence_guard=evidence_guard,
        contradiction_detector=contradiction_detector,
        confidence_scorer=confidence_scorer,
        claim_verifier=claim_verifier,
        perspective_selector=PerspectiveAwareCandidateSelector(),
        post_rerank_perspective_selector=PostRerankPerspectiveSelector(),
    )

    print("[4/4] Running analysis...")
    print("\nRetrieving and reranking evidence...")

    result = service.analyze(
        query=query,
        retrieval_top_k=settings.bm25_top_k,
        rerank_top_k=settings.rerank_top_n,
    )

    print("\n" + "=" * 80)
    print("MILITARY ANALYSIS")
    print("=" * 80)
    print(result.military_analysis.analysis_text)

    print("\n" + "=" * 80)
    print("LEGAL ANALYSIS")
    print("=" * 80)
    print(result.legal_analysis.analysis_text)

    print("\n" + "=" * 80)
    print("HISTORICAL ANALYSIS")
    print("=" * 80)
    print(result.historical_analysis.analysis_text)

    print("\n" + "=" * 80)
    print("CLAIM VERIFICATION")
    print("=" * 80)

    if result.claim_verification:
        for claim in result.claim_verification:
            print(f"- Claim: {claim.claim}")
            print(f"  Status: {claim.status.value.upper()}")
            print(f"  Support score: {claim.support_score:.2f}")
            print(f"  Verified: {claim.verified}")

            if claim.supporting_evidence_ids:
                print(
                    "  Supporting evidence: "
                    + ", ".join(claim.supporting_evidence_ids)
                )
            else:
                print("  Supporting evidence: None")
    else:
        print("No claims were generated for verification.")

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

    print("\n" + "=" * 80)
    print("CONFIDENCE")
    print("=" * 80)

    print(
        f"Final score: "
        f"{result.confidence.final_score:.2f}/100"
    )

    print(
        f"Confidence level: "
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
        f"Source reliability: "
        f"{result.confidence.source_reliability_score:.2f}"
    )

    print(
        f"Claim support: "
        f"{result.confidence.claim_support_score:.2f}"
    )

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

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()