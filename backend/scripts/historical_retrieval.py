from pathlib import Path

from app.modules.retrieval.hybrid_retriever import HybridRetriever
from app.modules.retrieval.perspective_query_builder import (
    PerspectiveQueryBuilder,
)
from app.domain.enums import Perspective
from app.core.config import Settings


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


focused_query = PerspectiveQueryBuilder().build(
    query,
    (Perspective.HISTORICAL,),
)[Perspective.HISTORICAL]


def source_name(chunk_id: str) -> str:
    """Classify a chunk ID by evidence source."""

    if chunk_id.startswith("un_peacemaker::"):
        return "UN Peacemaker"

    if chunk_id.startswith("ucdp-ged-"):
        return "UCDP GED"

    if chunk_id.startswith("ucdp-dyadic-"):
        return "UCDP Dyadic"

    if chunk_id.startswith("icrc::"):
        return "ICRC"

    if "sipri" in chunk_id.lower():
        return "SIPRI"

    if "acled" in chunk_id.lower():
        return "ACLED"

    return "Other"


def source_counts(results) -> dict[str, int]:
    """Count how many results came from each source."""

    counts: dict[str, int] = {}

    for result in results:
        source = source_name(result.chunk_id)
        counts[source] = counts.get(source, 0) + 1

    return counts


def print_results(title: str, results) -> None:
    """Print retrieval results."""

    print("\n" + "-" * 80)
    print(title)
    print("-" * 80)

    for rank, result in enumerate(results, 1):
        print(
            f"{rank:03d}. "
            f"{result.chunk_id} | "
            f"score={getattr(result, 'score', None)}"
        )


def find_matches(results, target_prefix: str):
    """Find all results matching a chunk/document prefix."""

    return [
        (rank, result)
        for rank, result in enumerate(results, 1)
        if result.chunk_id.startswith(target_prefix)
    ]


print("\n" + "=" * 80)
print("HISTORICAL RETRIEVAL DIAGNOSTIC")
print("=" * 80)

print("\nQUERY:")
print(focused_query)


# ============================================================================
# BM25
# ============================================================================

bm25_results = retriever.bm25_index.search(
    focused_query,
    top_k=200,
)

print_results(
    "BM25 TOP 200",
    bm25_results,
)


# ============================================================================
# FAISS
# ============================================================================

dense_results = retriever.faiss_index.search(
    focused_query,
    top_k=200,
)

print_results(
    "FAISS TOP 200",
    dense_results,
)


# ============================================================================
# HYBRID
# ============================================================================

hybrid_results = retriever.search(
    focused_query,
    top_k=200,
)

print("\n" + "-" * 80)
print("HYBRID TOP 200")
print("-" * 80)

for rank, result in enumerate(hybrid_results, 1):
    print(
        f"{rank:03d}. "
        f"{result.chunk_id} | "
        f"rrf={result.score:.6f} | "
        f"ranks={result.ranks}"
    )


# ============================================================================
# SOURCE COVERAGE
# ============================================================================

print("\n" + "=" * 80)
print("SOURCE COVERAGE")
print("=" * 80)

print("\nBM25:")
for source, count in sorted(
    source_counts(bm25_results).items(),
    key=lambda item: (-item[1], item[0]),
):
    print(f"  {source:<20} {count}")

print("\nFAISS:")
for source, count in sorted(
    source_counts(dense_results).items(),
    key=lambda item: (-item[1], item[0]),
):
    print(f"  {source:<20} {count}")

print("\nHYBRID:")
for source, count in sorted(
    source_counts(hybrid_results).items(),
    key=lambda item: (-item[1], item[0]),
):
    print(f"  {source:<20} {count}")


# ============================================================================
# TARGET DOCUMENTS
# ============================================================================

ukraine_peacemaker_prefix = (
    "un_peacemaker::"
    "un_peacemaker/ukraine/"
    "2014_peaceful_settlement_eastern_ukraine.pdf"
)

print("\n" + "=" * 80)
print("UKRAINE UN PEACEMAKER CHECK")
print("=" * 80)

for name, results in (
    ("BM25", bm25_results),
    ("FAISS", dense_results),
    ("HYBRID", hybrid_results),
):
    matches = find_matches(
        results,
        ukraine_peacemaker_prefix,
    )

    print(f"\n{name}:")

    if not matches:
        print("  NOT FOUND in top 200")
    else:
        for rank, result in matches:
            print(
                f"  rank={rank} | "
                f"{result.chunk_id} | "
                f"score={getattr(result, 'score', None)}"
            )


# ============================================================================
# SIPRI CHECK
# ============================================================================

print("\n" + "=" * 80)
print("SIPRI CHECK")
print("=" * 80)

for name, results in (
    ("BM25", bm25_results),
    ("FAISS", dense_results),
    ("HYBRID", hybrid_results),
):
    matches = [
        (rank, result)
        for rank, result in enumerate(results, 1)
        if source_name(result.chunk_id) == "SIPRI"
    ]

    print(f"\n{name}:")

    if not matches:
        print("  NO SIPRI RESULTS in top 200")
    else:
        for rank, result in matches:
            print(
                f"  rank={rank} | "
                f"{result.chunk_id} | "
                f"score={getattr(result, 'score', None)}"
            )


# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("DIAGNOSTIC SUMMARY")
print("=" * 80)

ukraine_bm25 = find_matches(
    bm25_results,
    ukraine_peacemaker_prefix,
)

ukraine_faiss = find_matches(
    dense_results,
    ukraine_peacemaker_prefix,
)

ukraine_hybrid = find_matches(
    hybrid_results,
    ukraine_peacemaker_prefix,
)

sipri_bm25 = [
    result
    for result in bm25_results
    if source_name(result.chunk_id) == "SIPRI"
]

sipri_faiss = [
    result
    for result in dense_results
    if source_name(result.chunk_id) == "SIPRI"
]

sipri_hybrid = [
    result
    for result in hybrid_results
    if source_name(result.chunk_id) == "SIPRI"
]


print(
    "\nUkraine UN Peacemaker:"
    f"\n  BM25  : {'FOUND' if ukraine_bm25 else 'NOT FOUND'}"
    f"\n  FAISS : {'FOUND' if ukraine_faiss else 'NOT FOUND'}"
    f"\n  Hybrid: {'FOUND' if ukraine_hybrid else 'NOT FOUND'}"
)

print(
    "\nSIPRI:"
    f"\n  BM25  : {'FOUND' if sipri_bm25 else 'NOT FOUND'}"
    f"\n  FAISS : {'FOUND' if sipri_faiss else 'NOT FOUND'}"
    f"\n  Hybrid: {'FOUND' if sipri_hybrid else 'NOT FOUND'}"
)

print("\n" + "=" * 80)
print("END DIAGNOSTIC")
print("=" * 80)