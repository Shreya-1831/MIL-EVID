from pathlib import Path

from app.core.config import Settings
from app.modules.retrieval.hybrid_retriever import HybridRetriever


settings = Settings()

BASE_DIR = Path(__file__).resolve().parents[1]

retriever = HybridRetriever.from_index_dirs(
    bm25_index_dir=BASE_DIR / settings.bm25_index_dir,
    faiss_index_dir=BASE_DIR / settings.faiss_index_dir,
)


queries = {
    "SIPRI arms transfers": (
        "Russia Ukraine arms transfers "
        "military equipment weapons suppliers recipients "
        "arms imports exports"
    ),
    "SIPRI military capabilities": (
        "Russia Ukraine military capabilities "
        "weapons military equipment defense procurement"
    ),
    "Ukraine historical": (
        "Russia Ukraine conflict historical escalation "
        "Minsk ceasefire settlement peace process"
    ),
}


for name, query in queries.items():
    print("\n" + "=" * 80)
    print(name.upper())
    print("=" * 80)
    print(f"\nQUERY: {query}")

    bm25 = retriever.bm25_index.search(
        query,
        top_k=50,
    )

    dense = retriever.faiss_index.search(
        query,
        top_k=50,
    )

    print("\nBM25 SIPRI:")
    found = False

    for rank, result in enumerate(bm25, 1):
        if result.chunk_id.startswith("sipri-"):
            print(
                f"  rank={rank} | "
                f"{result.chunk_id} | "
                f"score={result.score}"
            )
            found = True

    if not found:
        print("  NOT FOUND")

    print("\nFAISS SIPRI:")
    found = False

    for rank, result in enumerate(dense, 1):
        if result.chunk_id.startswith("sipri-"):
            print(
                f"  rank={rank} | "
                f"{result.chunk_id} | "
                f"score={result.score}"
            )
            found = True

    if not found:
        print("  NOT FOUND")