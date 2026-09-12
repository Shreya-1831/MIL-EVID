from pathlib import Path

from app.core.config import Settings
from app.modules.retrieval.bm25_index import BM25Index
from app.modules.retrieval.faiss_index import FaissIndex


settings = Settings()

BASE_DIR = Path(__file__).resolve().parents[1]

bm25_dir = BASE_DIR / settings.bm25_index_dir
faiss_dir = BASE_DIR / settings.faiss_index_dir

bm25 = BM25Index.load(index_dir=bm25_dir)
faiss_index = FaissIndex.load(index_dir=faiss_dir)


def source_name(chunk_id: str) -> str:
    chunk_id_lower = chunk_id.lower()

    if chunk_id.startswith("un_peacemaker::"):
        return "UN Peacemaker"

    if "sipri" in chunk_id_lower:
        return "SIPRI"

    if chunk_id.startswith("ucdp-ged-"):
        return "UCDP GED"

    if chunk_id.startswith("ucdp-dyadic-"):
        return "UCDP Dyadic"

    if chunk_id.startswith("icrc::"):
        return "ICRC"

    return "Other"


def get_source_counts(chunk_ids: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}

    for chunk_id in chunk_ids:
        source = source_name(chunk_id)
        counts[source] = counts.get(source, 0) + 1

    return counts


def find_matches(
    chunk_ids: list[str],
    prefix: str,
) -> list[str]:
    return [
        chunk_id
        for chunk_id in chunk_ids
        if chunk_id.startswith(prefix)
    ]


# ============================================================================
# INDEX INFORMATION
# ============================================================================

print("\n" + "=" * 80)
print("EXISTING INDEX CONTENT CHECK")
print("=" * 80)

print("\nBM25")
print("-" * 80)
print(f"Path: {bm25_dir}")
print(f"Chunks: {bm25.size}")
print(f"Fingerprint: {bm25.corpus_fingerprint}")

print("\nFAISS")
print("-" * 80)
print(f"Path: {faiss_dir}")
print(f"Chunks: {faiss_index.size}")
print(f"Dimension: {faiss_index.dimension}")
print(f"Model: {faiss_index.model_name}")


# ============================================================================
# SOURCE COUNTS
# ============================================================================

print("\n" + "=" * 80)
print("BM25 SOURCE COUNTS")
print("=" * 80)

for source, count in sorted(
    get_source_counts(bm25._chunk_ids).items(),
    key=lambda item: (-item[1], item[0]),
):
    print(f"{source:<20} {count}")


print("\n" + "=" * 80)
print("FAISS SOURCE COUNTS")
print("=" * 80)

for source, count in sorted(
    get_source_counts(faiss_index._chunk_ids).items(),
    key=lambda item: (-item[1], item[0]),
):
    print(f"{source:<20} {count}")


# ============================================================================
# UKRAINE UN PEACEMAKER
# ============================================================================

ukraine_prefix = (
    "un_peacemaker::"
    "un_peacemaker/ukraine/"
    "2014_peaceful_settlement_eastern_ukraine.pdf"
)

bm25_ukraine = find_matches(
    bm25._chunk_ids,
    ukraine_prefix,
)

faiss_ukraine = find_matches(
    faiss_index._chunk_ids,
    ukraine_prefix,
)


print("\n" + "=" * 80)
print("UKRAINE UN PEACEMAKER")
print("=" * 80)

print("\nBM25:")

if bm25_ukraine:
    print(f"FOUND — {len(bm25_ukraine)} chunks")

    for chunk_id in bm25_ukraine:
        print(f"  {chunk_id}")
else:
    print("NOT FOUND")


print("\nFAISS:")

if faiss_ukraine:
    print(f"FOUND — {len(faiss_ukraine)} chunks")

    for chunk_id in faiss_ukraine:
        print(f"  {chunk_id}")
else:
    print("NOT FOUND")


# ============================================================================
# ALL UKRAINE UN PEACEMAKER CHUNKS
# ============================================================================

ukraine_prefix_all = "un_peacemaker::un_peacemaker/ukraine/"

bm25_all_ukraine = find_matches(
    bm25._chunk_ids,
    ukraine_prefix_all,
)

faiss_all_ukraine = find_matches(
    faiss_index._chunk_ids,
    ukraine_prefix_all,
)


print("\n" + "=" * 80)
print("ALL UKRAINE UN PEACEMAKER CHUNKS")
print("=" * 80)

print("\nBM25:")
print(f"Total: {len(bm25_all_ukraine)}")

for chunk_id in bm25_all_ukraine[:20]:
    print(f"  {chunk_id}")

if len(bm25_all_ukraine) > 20:
    print(f"  ... and {len(bm25_all_ukraine) - 20} more")


print("\nFAISS:")
print(f"Total: {len(faiss_all_ukraine)}")

for chunk_id in faiss_all_ukraine[:20]:
    print(f"  {chunk_id}")

if len(faiss_all_ukraine) > 20:
    print(f"  ... and {len(faiss_all_ukraine) - 20} more")


# ============================================================================
# SIPRI
# ============================================================================

bm25_sipri = [
    chunk_id
    for chunk_id in bm25._chunk_ids
    if "sipri" in chunk_id.lower()
]

faiss_sipri = [
    chunk_id
    for chunk_id in faiss_index._chunk_ids
    if "sipri" in chunk_id.lower()
]


print("\n" + "=" * 80)
print("SIPRI")
print("=" * 80)

print("\nBM25:")

if bm25_sipri:
    print(f"FOUND — {len(bm25_sipri)} chunks")

    for chunk_id in bm25_sipri[:20]:
        print(f"  {chunk_id}")

    if len(bm25_sipri) > 20:
        print(f"  ... and {len(bm25_sipri) - 20} more")
else:
    print("NOT FOUND")


print("\nFAISS:")

if faiss_sipri:
    print(f"FOUND — {len(faiss_sipri)} chunks")

    for chunk_id in faiss_sipri[:20]:
        print(f"  {chunk_id}")

    if len(faiss_sipri) > 20:
        print(f"  ... and {len(faiss_sipri) - 20} more")
else:
    print("NOT FOUND")


# ============================================================================
# FINAL DIAGNOSIS
# ============================================================================

print("\n" + "=" * 80)
print("FINAL INDEX DIAGNOSIS")
print("=" * 80)

print(
    "\nUkraine UN Peacemaker:"
    f"\n  BM25  = {'PRESENT' if bm25_ukraine else 'MISSING'}"
    f"\n  FAISS = {'PRESENT' if faiss_ukraine else 'MISSING'}"
)

print(
    "\nSIPRI:"
    f"\n  BM25  = {'PRESENT' if bm25_sipri else 'MISSING'}"
    f"\n  FAISS = {'PRESENT' if faiss_sipri else 'MISSING'}"
)

print("\n" + "=" * 80)
print("NO INDEXES WERE MODIFIED")
print("=" * 80)