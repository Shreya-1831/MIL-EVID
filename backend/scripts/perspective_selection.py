from pathlib import Path

from app.core.config import Settings
from app.domain.enums import Perspective
from app.domain.models.analysis import AnalysisEvidence
from app.modules.analysis.post_rerank_perspective_selector import (
    PostRerankPerspectiveSelector,
)
from app.modules.retrieval.hybrid_retriever import HybridRetriever
from app.modules.retrieval.perspective_query_builder import (
    PerspectiveQueryBuilder,
)
from app.modules.retrieval.reranker import CrossEncoderReranker
from app.repositories.chunk_file_store import get_chunks_by_id
from app.modules.analysis.perspective_selector import PerspectiveAwareCandidateSelector
from app.modules.analysis.evidence_guard import EvidenceConsistencyGuard

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

perspectives = (
    Perspective.MILITARY,
    Perspective.LEGAL,
    Perspective.HISTORICAL,
)

query_builder = PerspectiveQueryBuilder()

focused_queries = query_builder.build(
    query,
    perspectives,
)


# ============================================================================
# HYBRID RETRIEVAL
# ============================================================================

hybrid_results = []

for perspective in perspectives:
    perspective_query = focused_queries[perspective]

    if isinstance(perspective_query, tuple):
        queries = perspective_query
    else:
        queries = (perspective_query,)

    for focused_query in queries:
        results = retriever.search(
            focused_query,
            top_k=100,
        )

        hybrid_results.extend(results)

        # Military auxiliary retrieval.
        if perspective == Perspective.MILITARY:
            military_query = (
                f"{query} "
                "Russia Ukraine arms transfers weapons military equipment "
                "suppliers recipients deliveries imports exports"
            )

            military_results = retriever.search(
                military_query,
                top_k=100,
            )

            hybrid_results.extend(military_results)


# Remove duplicates.

seen_ids = set()
unique_hybrid = []

for result in hybrid_results:
    if result.chunk_id in seen_ids:
        continue

    seen_ids.add(result.chunk_id)
    unique_hybrid.append(result)

hybrid_results = unique_hybrid

chunk_store_dir = BASE_DIR / "data" / "processed" / "chunks"

all_chunks_by_id = get_chunks_by_id(
    [result.chunk_id for result in hybrid_results],
    chunk_store_dir=chunk_store_dir,
)

selector = PerspectiveAwareCandidateSelector(
    preserve_per_perspective=5,
    max_candidates=30,
)

selection = selector.select(
    query=query,
    candidates=hybrid_results,
    evidence_by_id=all_chunks_by_id,
)

print("\n" + "-" * 80)
print("PRE-RERANK PERSPECTIVE SELECTION")
print("-" * 80)

for rank, result in enumerate(selection.candidates, 1):
    chunk = all_chunks_by_id.get(result.chunk_id)

    print(
        f"{rank:02d}. "
        f"{result.chunk_id} | "
        f"source={chunk.source if chunk else 'UNKNOWN'} | "
        f"perspective={chunk.perspective if chunk else 'UNKNOWN'}"
    )

print("\n" + "=" * 80)
print("THREE-PERSPECTIVE RETRIEVAL → RERANK → SELECTION")
print("=" * 80)

print(f"\nHybrid candidates: {len(hybrid_results)}")


# ============================================================================
# RERANK
# ============================================================================

# candidate_results = hybrid_results[:100]
candidate_results = selection.candidates

chunk_store_dir = BASE_DIR / "data" / "processed" / "chunks"

chunks_by_id = get_chunks_by_id(
    [result.chunk_id for result in candidate_results],
    chunk_store_dir=chunk_store_dir,
)

chunk_texts = {
    chunk_id: chunk.text
    for chunk_id, chunk in chunks_by_id.items()
}

print(f"Reranker candidates: {len(candidate_results)}")
print(f"Chunk texts loaded: {len(chunk_texts)}")


reranker = CrossEncoderReranker(
    model_name=settings.reranker_model,
)

reranked = reranker.rerank(
    query=query,
    candidates=candidate_results,
    chunk_texts=chunk_texts,
    top_k=len(candidate_results),
)


# ============================================================================
# RERANKED RESULTS
# ============================================================================

print("\n" + "-" * 80)
print("RERANKED TOP 15")
print("-" * 80)

for rank, result in enumerate(reranked, 1):
    print(
        f"{rank:02d}. "
        f"{result.chunk_id} | "
        f"score={result.score:.6f}"
    )


# ============================================================================
# CONVERT TO AnalysisEvidence
# ============================================================================

evidence = []

for result in reranked:
    chunk = chunks_by_id[result.chunk_id]

    evidence.append(
        AnalysisEvidence(
            evidence_id=result.chunk_id,
            source=chunk.source,
            source_type=chunk.source_type,
            perspective=chunk.perspective,
            title=chunk.title,
            text=chunk.text,
            reranker_score=result.score,
            original_rrf_score=result.original_rrf_score,
            ranks=result.ranks,
        )
    )


# ============================================================================
# POST-RERANK SELECTION
# ============================================================================

selector = PostRerankPerspectiveSelector()

selected = selector.select(
    query=query,
    evidence=evidence,
    max_evidence=10,
)

guard = EvidenceConsistencyGuard()

print("\n" + "-" * 80)
print("EVIDENCE GUARD CHECK")
print("-" * 80)

guarded_direct = []
guarded_contextual = []

for perspective in (
    Perspective.MILITARY,
    Perspective.LEGAL,
    Perspective.HISTORICAL,
):
    perspective_evidence = tuple(
        item
        for item in selected
        if (
            (
                item.source in {"UCDP GED", "UCDP Dyadic"}
                and perspective == Perspective.MILITARY
            )
            or (
                item.source not in {"UCDP GED", "UCDP Dyadic"}
                and item.perspective == perspective
            )
        )
    )

    if not perspective_evidence:
        continue
    
    if perspective == Perspective.HISTORICAL:
        print("\nHISTORICAL TOPIC DEBUG")
        print("QUERY TOPICS:", guard._extract_topics(query))

        for item in perspective_evidence:
            print(f"\n{item.evidence_id}")
            print(
                "EVIDENCE TOPICS:",
                guard._extract_topics(f"{item.title} {item.text}"),
            )

    result = guard.filter(
        query=query,
        evidence=perspective_evidence,
        perspective=perspective.value,
    )

    print(f"\n{perspective.value.upper()}")

    print(f"  input      : {len(perspective_evidence)}")
    print(f"  direct     : {len(result.direct_evidence)}")
    print(f"  contextual : {len(result.contextual_evidence)}")

    for item in result.contextual_evidence:
        print(f"  CONTEXTUAL: {item.evidence_id}")

    guarded_direct.extend(result.direct_evidence)
    guarded_contextual.extend(result.contextual_evidence)

print("\n" + "-" * 80)
print("UN PEACEMAKER AFTER EVIDENCE GUARD")
print("-" * 80)

for item in guarded_direct:
    if item.source == "UN Peacemaker":
        print(f"DIRECT: {item.evidence_id}")

for item in guarded_contextual:
    if item.source == "UN Peacemaker":
        print(f"CONTEXTUAL: {item.evidence_id}")

print("\n" + "-" * 80)
print("AFTER POST-RERANK SELECTION")
print("-" * 80)

for rank, item in enumerate(selected, 1):
    print(
        f"{rank:02d}. "
        f"{item.evidence_id} | "
        f"source={item.source}"
    )


# ============================================================================
# SOURCE COUNTS
# ============================================================================

counts = {}

for item in selected:
    counts[item.source] = counts.get(item.source, 0) + 1

print("\n" + "-" * 80)
print("SELECTED SOURCE COUNTS")
print("-" * 80)

for source, count in sorted(counts.items()):
    print(f"{source:<25} {count}")


# ============================================================================
# HISTORICAL CHECK
# ============================================================================

historical_selected = [
    item
    for item in selected
    if item.source == "UN Peacemaker"
]

print("\n" + "-" * 80)
print("HISTORICAL / UN PEACEMAKER CHECK")
print("-" * 80)

if historical_selected:
    print(f"FOUND: {len(historical_selected)} UN Peacemaker items")

    for item in historical_selected:
        print(f"  {item.evidence_id}")
else:
    print("NOT FOUND")


print("\n" + "=" * 80)
print("END DIAGNOSTIC")
print("=" * 80)