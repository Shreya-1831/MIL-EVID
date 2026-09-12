from app.core.config import get_settings
from app.modules.retrieval.hybrid_retriever import HybridRetriever
from pathlib import Path

def main() -> None:
    settings = get_settings()

    retriever = HybridRetriever.from_index_dirs(
        bm25_index_dir=Path(settings.bm25_index_dir),
        faiss_index_dir=Path(settings.faiss_index_dir),
    )

    query = (
        "How should the escalation of the Russia–Ukraine conflict be assessed "
        "from military, legal, and historical perspectives, particularly regarding "
        "attacks on civilian areas, damage to essential infrastructure, civilian "
        "protection, and competing claims about responsibility? "
        "international humanitarian law IHL civilian protection distinction "
        "proportionality precautions targeting civilian objects responsibility "
        "lawful unlawful war crimes ICRC"
    )

    print("=" * 80)
    print("LEGAL RETRIEVAL TEST")
    print("=" * 80)

    for k in (50, 100, 200):
        results = retriever.search(
            query,
            top_k=50,
            bm25_top_k=k,
            dense_top_k=k,
        )

        icrc = [
            result
            for result in results
            if result.chunk_id.startswith("icrc")
        ]

        print(f"\nK={k}")
        print(f"Hybrid results: {len(results)}")
        print(f"ICRC results: {len(icrc)}")

        for result in icrc[:5]:
            print(
                f"  {result.chunk_id} | "
                f"score={result.score:.4f} | "
                f"ranks={result.ranks}"
            )


if __name__ == "__main__":
    main()