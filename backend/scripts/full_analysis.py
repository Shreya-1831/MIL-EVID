"""Run the complete MIL-EVID retrieval and analysis pipeline."""

from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.modules.analysis.analyzer import EvidenceAnalyzer
from app.modules.analysis.context_builder import EvidenceContextBuilder
from app.modules.analysis.llm_client import OllamaClient
from app.modules.retrieval.hybrid_retriever import HybridRetriever
from app.modules.retrieval.reranker import CrossEncoderReranker
from app.services.analysis_service import AnalysisService


def main() -> None:
    settings = get_settings()

    print("=" * 80)
    print("MIL-EVID — FULL ANALYSIS PIPELINE")
    print("=" * 80)

    query = input("\nEnter your military situation query:\n> ").strip()

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

    context_builder = EvidenceContextBuilder(
        chunk_store_dir=Path(settings.chunk_store_dir),
    )

    llm_client = OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )

    analyzer = EvidenceAnalyzer(
        llm_client=llm_client,
    )

    service = AnalysisService(
        retriever=retriever,
        reranker=reranker,
        context_builder=context_builder,
        analyzer=analyzer,
    )

    print("[4/4] Running analysis...")
    print("\nRetrieving and reranking evidence...")

    military, legal, historical = service.analyze(
        query=query,
        retrieval_top_k=settings.bm25_top_k,
        # rerank_top_k=settings.rerank_top_n,
        rerank_top_k=8,
    )

    print("\n" + "=" * 80)
    print("MILITARY ANALYSIS")
    print("=" * 80)
    print(military.analysis_text)

    print("\n" + "=" * 80)
    print("LEGAL ANALYSIS")
    print("=" * 80)
    print(legal.analysis_text)

    print("\n" + "=" * 80)
    print("HISTORICAL ANALYSIS")
    print("=" * 80)
    print(historical.analysis_text)

    print("\n" + "=" * 80)
    print("EVIDENCE USED")
    print("=" * 80)

    for evidence_id in military.evidence_ids:
        print(f"- {evidence_id}")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()