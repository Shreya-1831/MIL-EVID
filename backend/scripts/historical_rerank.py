"""
Diagnostic for Historical retrieval through reranking.

Pipeline tested:

    Historical focused queries
        ↓
    Hybrid retrieval
        ↓
    Top 15 candidates
        ↓
    Cross-encoder reranker
        ↓
    UN Peacemaker check
"""

from pathlib import Path

from app.core.config import Settings
from app.domain.enums import Perspective
from app.modules.retrieval.hybrid_retriever import HybridRetriever
from app.modules.retrieval.perspective_query_builder import (
    PerspectiveQueryBuilder,
)
from app.modules.retrieval.reranker import CrossEncoderReranker
from app.repositories.chunk_file_store import get_chunks_by_id


settings = Settings()

BASE_DIR = Path(__file__).resolve().parents[1]

retriever = HybridRetriever.from_index_dirs(
    bm25_index_dir=BASE_DIR / settings.bm25_index_dir,
    faiss_index_dir=BASE_DIR / settings.faiss_index_dir,
)


query = (
    "How should the escalation of the Russia–Ukraine conflict be assessed "
    "from military, legal, and historical perspectives, particularly regarding "
    "attacks on civilian areas, damage to essential infrastructure, civilian "
    "protection, and competing claims about responsibility?"
)


# ============================================================================
# HISTORICAL QUERIES
# ============================================================================

focused_queries = PerspectiveQueryBuilder().build(
    query,
    (Perspective.HISTORICAL,),
)[Perspective.HISTORICAL]

if isinstance(focused_queries, str):
    focused_queries = (focused_queries,)


print("\n" + "=" * 80)
print("HYBRID → RERANKER DIAGNOSTIC")
print("=" * 80)

print("\nHISTORICAL QUERIES:")

for index, focused_query in enumerate(focused_queries, 1):
    print(f"{index}. {focused_query}")


# ============================================================================
# HYBRID RETRIEVAL
# ============================================================================

hybrid_results = []

for focused_query in focused_queries:
    results = retriever.search(
        focused_query,
        top_k=100,
    )

    hybrid_results.extend(results)


# Remove duplicate chunk IDs while preserving order.

seen_ids: set[str] = set()
unique_hybrid_results = []

for result in hybrid_results:
    if result.chunk_id in seen_ids:
        continue

    seen_ids.add(result.chunk_id)
    unique_hybrid_results.append(result)


hybrid_results = unique_hybrid_results[:100]


print("\n" + "-" * 80)
print("HYBRID CANDIDATES")
print("-" * 80)

print(f"Total unique candidates: {len(hybrid_results)}")

for rank, result in enumerate(hybrid_results, 1):
    print(
        f"{rank:03d}. "
        f"{result.chunk_id} | "
        f"rrf={result.score:.6f} | "
        f"ranks={result.ranks}"
    )


# ============================================================================
# UN PEACEMAKER CHECK BEFORE RERANKING
# ============================================================================

ukraine_peacemaker_prefix = (
    "un_peacemaker::"
    "un_peacemaker/ukraine/"
    "2014_peaceful_settlement_eastern_ukraine.pdf"
)


print("\n" + "-" * 80)
print("UN PEACEMAKER BEFORE RERANKING")
print("-" * 80)

hybrid_matches = [
    (rank, result)
    for rank, result in enumerate(hybrid_results, 1)
    if result.chunk_id.startswith(ukraine_peacemaker_prefix)
]

if not hybrid_matches:
    print("NOT FOUND")
else:
    for rank, result in hybrid_matches:
        print(
            f"rank={rank} | "
            f"{result.chunk_id} | "
            f"rrf={result.score:.6f}"
        )


# ============================================================================
# LOAD TEXT FOR RERANKING
# ============================================================================

candidate_ids = [
    result.chunk_id
    for result in hybrid_results[:15]
]

chunk_store_dir = BASE_DIR / "data" / "processed" / "chunks"

chunks_by_id = get_chunks_by_id(
    candidate_ids,
    chunk_store_dir=chunk_store_dir,
)


chunk_texts = {
    chunk_id: chunk.text
    for chunk_id, chunk in chunks_by_id.items()
}


print("\n" + "-" * 80)
print("RERANKER INPUT")
print("-" * 80)

print(f"Candidates passed to reranker: {len(candidate_ids)}")
print(f"Chunk texts loaded: {len(chunk_texts)}")


# ============================================================================
# RERANK
# ============================================================================

reranker = CrossEncoderReranker(
    model_name=settings.reranker_model,
)


reranked_results = reranker.rerank(
    query=query,
    candidates=hybrid_results[:15],
    chunk_texts=chunk_texts,
    top_k=15,
)


# ============================================================================
# RERANKED RESULTS
# ============================================================================

print("\n" + "-" * 80)
print("RERANKED TOP 15")
print("-" * 80)

for rank, result in enumerate(reranked_results, 1):
    print(
        f"{rank:02d}. "
        f"{result.chunk_id} | "
        f"score={result.score:.6f} | "
        f"original_rrf={result.original_rrf_score:.6f}"
    )


# ============================================================================
# UN PEACEMAKER AFTER RERANKING
# ============================================================================

print("\n" + "-" * 80)
print("UN PEACEMAKER AFTER RERANKING")
print("-" * 80)

reranked_matches = [
    (rank, result)
    for rank, result in enumerate(reranked_results, 1)
    if result.chunk_id.startswith(ukraine_peacemaker_prefix)
]

if not reranked_matches:
    print("NOT FOUND")
else:
    for rank, result in reranked_matches:
        print(
            f"rank={rank} | "
            f"{result.chunk_id} | "
            f"score={result.score:.6f}"
        )


# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("DIAGNOSTIC SUMMARY")
print("=" * 80)

print(
    "\nUN Peacemaker:"
    f"\n  Hybrid retrieval : "
    f"{'FOUND' if hybrid_matches else 'NOT FOUND'}"
    f"\n  After reranking  : "
    f"{'FOUND' if reranked_matches else 'NOT FOUND'}"
)

print(
    "\nReranker:"
    f"\n  Input candidates : {len(candidate_ids)}"
    f"\n  Output candidates: {len(reranked_results)}"
)

print("\n" + "=" * 80)
print("END DIAGNOSTIC")
print("=" * 80)