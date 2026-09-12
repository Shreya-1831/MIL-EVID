from pathlib import Path

from app.repositories.chunk_file_store import iter_all_chunks
from app.core.config import Settings


settings = Settings()

BASE_DIR = Path(__file__).resolve().parents[1]

chunk_dir = BASE_DIR / settings.chunk_store_dir


print("\n" + "=" * 80)
print("SIPRI CONTENT CHECK")
print("=" * 80)

count = 0

for chunk in iter_all_chunks(chunk_dir):
    if not chunk.id.startswith("sipri-"):
        continue

    text = chunk.text.lower()

    if (
        "russia" in text
        or "ukraine" in text
        or "soviet" in text
    ):
        count += 1

        print("\n" + "-" * 80)
        print(chunk.id)
        print("-" * 80)
        print(chunk.text[:1000])

        if count >= 10:
            break


print("\n" + "=" * 80)
print(f"DISPLAYED {count} RELEVANT SIPRI CHUNKS")
print("=" * 80)