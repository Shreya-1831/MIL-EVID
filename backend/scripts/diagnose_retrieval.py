from __future__ import annotations

from collections import Counter
from pathlib import Path

from app.core.config import get_settings
from app.modules.retrieval.hybrid_retriever import HybridRetriever
from app.modules.retrieval.reranker import CrossEncoderReranker
from app.repositories.chunk_file_store import get_chunks_by_id


QUERY = (
    # "The Russia–Ukraine conflict escalates around a major Ukrainian city, "
    # "with repeated attacks damaging residential buildings and essential "
    # "infrastructure. What military, legal, and historical considerations "
    # "should be considered when assessing the escalation, protecting "
    # "civilians, and evaluating the claims made about the attacks?"
    "How should military tensions between India and Pakistan be assessed "
    "from military, legal, and historical perspectives, particularly regarding "
    "attacks, civilian protection, and escalation?"
)


def main() -> None:
    settings = get_settings()

    print("=" * 100)
    print("MIL-EVID — RETRIEVAL SOURCE DISTRIBUTION DIAGNOSTIC")
    print("=" * 100)
    print(f"\nQuery: {QUERY}\n")

    # ---------------------------------------------------------------
    # 1. Load hybrid retriever
    # ---------------------------------------------------------------
    retriever = HybridRetriever.from_index_dirs(
        bm25_index_dir=Path(settings.bm25_index_dir),
        faiss_index_dir=Path(settings.faiss_index_dir),
        rrf_k=settings.rrf_k,
    )

    # ---------------------------------------------------------------
    # 2. Hybrid retrieval
    # ---------------------------------------------------------------
    hybrid_results = retriever.search(
        QUERY,
        top_k=50,
        bm25_top_k=settings.bm25_top_k,
        dense_top_k=settings.dense_top_k,
    )

    print("=" * 100)
    print("HYBRID / RRF — TOP 50")
    print("=" * 100)

    chunk_ids = [r.chunk_id for r in hybrid_results]

    chunks = get_chunks_by_id(
        chunk_ids,
        chunk_store_dir=Path(settings.chunk_store_dir),
    )

    def source_of(chunk_id: str) -> str:
        chunk = chunks.get(chunk_id)
        if chunk is None:
            return "MISSING"
        return str(chunk.source)

    counter = Counter(source_of(r.chunk_id) for r in hybrid_results)

    print("\nSOURCE DISTRIBUTION:")
    for source, count in counter.most_common():
        print(f"  {source}: {count}")

    print("\nTOP RESULTS:")
    for rank, result in enumerate(hybrid_results, start=1):
        chunk = chunks.get(result.chunk_id)

        if chunk is None:
            print(
                f"{rank:>2}. RRF={result.score:.6f} | "
                f"{result.chunk_id} | MISSING"
            )
            continue

        print(
            f"{rank:>2}. "
            f"RRF={result.score:.6f} | "
            f"SOURCE={chunk.source} | "
            f"PERSPECTIVE={chunk.perspective} | "
            f"ID={result.chunk_id}"
        )

    # ---------------------------------------------------------------
    # 3. Cross-encoder reranking
    # ---------------------------------------------------------------
    reranker = CrossEncoderReranker(
        model_name=settings.reranker_model,
    )

    reranked = reranker.rerank(
        query=QUERY,
        candidates=hybrid_results,
        chunk_texts={
            chunk_id: chunk.text
            for chunk_id, chunk in chunks.items()
        },
        top_k=len(hybrid_results),
    )

    print("\n" + "=" * 100)
    print("CROSS-ENCODER — ALL CANDIDATES")
    print("=" * 100)

    counter = Counter(source_of(r.chunk_id) for r in reranked)

    print("\nSOURCE DISTRIBUTION:")
    for source, count in counter.most_common():
        print(f"  {source}: {count}")

    print("\nTOP RESULTS:")
    for rank, result in enumerate(reranked, start=1):
        chunk = chunks.get(result.chunk_id)

        if chunk is None:
            continue

        print(
            f"{rank:>2}. "
            f"CE={result.score:.6f} | "
            f"RRF={result.original_rrf_score:.6f} | "
            f"SOURCE={chunk.source} | "
            f"PERSPECTIVE={chunk.perspective} | "
            f"ID={result.chunk_id}"
        )

    # ---------------------------------------------------------------
    # 4. Final source summary
    # ---------------------------------------------------------------
    print("\n" + "=" * 100)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 100)

    print("\nHybrid source counts:")
    for source, count in Counter(
        source_of(r.chunk_id) for r in hybrid_results
    ).most_common():
        print(f"  {source}: {count}")

    print("\nCross-encoder source counts:")
    for source, count in Counter(
        source_of(r.chunk_id) for r in reranked
    ).most_common():
        print(f"  {source}: {count}")

    print("\nDiagnostic complete.")


if __name__ == "__main__":
    main()