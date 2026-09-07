from __future__ import annotations

import time
from pathlib import Path
from app.core.config import get_settings
from app.modules.retrieval.hybrid_retriever import HybridRetriever
from app.modules.retrieval.reranker import CrossEncoderReranker
from app.repositories.chunk_file_store import get_chunks_by_id


QUERY = "military conflict and civilian protection"


def main() -> None:
    settings = get_settings()

    print("=" * 80)
    print("MIL-EVID — PHASE 9 CROSS-ENCODER RERANKING TEST")
    print("=" * 80)

    print(f"\nQuery: {QUERY}")
    print(f"Embedding model: {settings.embedding_model}")
    print(f"Reranker model: {settings.reranker_model}")

    # ------------------------------------------------------------------
    # 1. Load hybrid retrieval indexes
    # ------------------------------------------------------------------

    print("\n[1/5] Loading BM25 + FAISS indexes...")

    start = time.perf_counter()

    retriever = HybridRetriever.from_index_dirs(
        bm25_index_dir=Path(settings.bm25_index_dir),
        faiss_index_dir=Path(settings.faiss_index_dir),
        rrf_k=settings.rrf_k,
    )

    elapsed = time.perf_counter() - start

    print(f"      Loaded in {elapsed:.2f}s")

    # ------------------------------------------------------------------
    # 2. Hybrid retrieval
    # ------------------------------------------------------------------

    print("\n[2/5] Running hybrid retrieval...")

    start = time.perf_counter()

    hybrid_results = retriever.search(
        QUERY,
        top_k=settings.rerank_top_n,
        bm25_top_k=settings.bm25_top_k,
        dense_top_k=settings.dense_top_k,
    )

    elapsed = time.perf_counter() - start

    print(
        f"      Retrieved {len(hybrid_results)} candidates "
        f"in {elapsed:.2f}s"
    )

    if not hybrid_results:
        print("\nNo hybrid candidates returned.")
        return

    # ------------------------------------------------------------------
    # 3. Load actual chunk text
    # ------------------------------------------------------------------

    print("\n[3/5] Loading candidate chunk text...")

    chunk_ids = [
        result.chunk_id
        for result in hybrid_results
    ]

    start = time.perf_counter()

    chunks = get_chunks_by_id(
        chunk_ids,
        chunk_store_dir=Path(settings.chunk_store_dir),
    )

    elapsed = time.perf_counter() - start

    print(
        f"      Loaded {len(chunks)}/{len(chunk_ids)} "
        f"chunk texts in {elapsed:.2f}s"
    )

    missing_ids = [
        chunk_id
        for chunk_id in chunk_ids
        if chunk_id not in chunks
    ]

    if missing_ids:
        print("\nWARNING: Missing chunk text:")
        for chunk_id in missing_ids:
            print(f"  - {chunk_id}")

    # Keep only candidates for which actual evidence text exists.
    rerank_candidates = [
        result
        for result in hybrid_results
        if result.chunk_id in chunks
    ]

    chunk_texts = {
        chunk_id: chunks[chunk_id].text
        for chunk_id in chunks
    }

    if not rerank_candidates:
        print("\nNo candidates have available text.")
        return

    # ------------------------------------------------------------------
    # 4. Load Cross-Encoder
    # ------------------------------------------------------------------

    print("\n[4/5] Loading Cross-Encoder...")

    start = time.perf_counter()

    reranker = CrossEncoderReranker(
        model_name=settings.reranker_model,
    )

    elapsed = time.perf_counter() - start

    print(
        f"      Model loaded in {elapsed:.2f}s"
    )

    # ------------------------------------------------------------------
    # 5. Rerank
    # ------------------------------------------------------------------

    print("\n[5/5] Reranking candidates...")

    start = time.perf_counter()

    reranked = reranker.rerank(
        query=QUERY,
        candidates=rerank_candidates,
        chunk_texts=chunk_texts,
        top_k=settings.rerank_top_n,
    )

    elapsed = time.perf_counter() - start

    print(
        f"      Reranked {len(rerank_candidates)} candidates "
        f"in {elapsed:.2f}s"
    )

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("HYBRID RANKING")
    print("=" * 80)

    for rank, result in enumerate(hybrid_results, start=1):
        print(
            f"{rank:>2}. "
            f"RRF={result.score:.6f} | "
            f"{result.chunk_id}"
        )

    print("\n" + "=" * 80)
    print("CROSS-ENCODER RERANKING")
    print("=" * 80)

    for rank, result in enumerate(reranked, start=1):
        print(
            f"{rank:>2}. "
            f"CE={result.score:.6f} | "
            f"RRF={result.original_rrf_score:.6f} | "
            f"{result.chunk_id}"
        )

    print("\n" + "=" * 80)
    print("TOP EVIDENCE TEXT")
    print("=" * 80)

    for rank, result in enumerate(reranked[:5], start=1):
        chunk = chunks[result.chunk_id]

        print(f"\n[{rank}] {result.chunk_id}")
        print(f"Cross-Encoder score: {result.score:.6f}")
        print(f"RRF score: {result.original_rrf_score:.6f}")
        print("-" * 80)
        print(chunk.text[:1000])

    print("\n" + "=" * 80)
    print("PHASE 9 INTEGRATION TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()