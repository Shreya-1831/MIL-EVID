"""
Build the BM25 and FAISS retrieval indexes from the local chunk store.

This is the integration/build path for the real ~104K-chunk corpus.
It is a standalone script, not a pytest test.

Usage:
    python -m scripts.build_indexes
    python -m scripts.build_indexes --rebuild
    python -m scripts.build_indexes --only bm25
    python -m scripts.build_indexes --only faiss
    python -m scripts.build_indexes --only faiss --rebuild
    python -m scripts.build_indexes --only faiss --rebuild --batch-size 64
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.modules.retrieval.bm25_index import BM25Index
from app.modules.retrieval.faiss_index import (
    EMBEDDING_BATCH_SIZE,
    FaissIndex,
)

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# BM25
# ---------------------------------------------------------------------------

def build_bm25(
    *,
    chunk_store_dir: Path,
    index_dir: Path,
    rebuild: bool,
) -> None:
    """Build and persist the BM25 index."""

    if not rebuild and BM25Index.exists(index_dir=index_dir):
        print(
            f"BM25 index already exists at {index_dir}; "
            "skipping (use --rebuild to force)."
        )
        return

    print("Building BM25 index...")
    start = time.monotonic()

    index = BM25Index.build(
        chunk_store_dir=chunk_store_dir,
    )

    index.save(
        index_dir=index_dir,
    )

    elapsed = time.monotonic() - start

    print(
        f"BM25 index built: "
        f"{index.size:,} chunks "
        f"in {elapsed:.1f}s "
        f"-> {index_dir}"
    )


# ---------------------------------------------------------------------------
# FAISS
# ---------------------------------------------------------------------------

def build_faiss(
    *,
    chunk_store_dir: Path,
    index_dir: Path,
    model_name: str,
    rebuild: bool,
    batch_size: int,
) -> None:
    """Build and persist the FAISS dense index with live progress."""

    if not rebuild and FaissIndex.exists(index_dir=index_dir):
        print(
            f"FAISS index already exists at {index_dir}; "
            "skipping (use --rebuild to force)."
        )
        return

    print()
    print("Building FAISS dense index...")
    print(f"Embedding model : {model_name}")
    print(f"Batch size      : {batch_size}")
    print("Progress        : enabled")
    print()

    start = time.monotonic()
    last_report_time = start
    last_report_count = 0

    def progress_callback(processed_count: int) -> None:
        """Print embedding progress as batches complete."""

        nonlocal last_report_time
        nonlocal last_report_count

        now = time.monotonic()

        # Print at least once every ~2 seconds.
        if (
            now - last_report_time < 2.0
            and processed_count != last_report_count
        ):
            return

        elapsed = now - start

        count_delta = processed_count - last_report_count
        time_delta = max(now - last_report_time, 1e-6)

        recent_rate = count_delta / time_delta
        overall_rate = processed_count / max(elapsed, 1e-6)

        print(
            f"FAISS embedding progress: "
            f"{processed_count:,} chunks | "
            f"elapsed {elapsed / 60:.1f} min | "
            f"recent {recent_rate:.1f} chunks/s | "
            f"overall {overall_rate:.1f} chunks/s",
            flush=True,
        )

        last_report_time = now
        last_report_count = processed_count

    index = FaissIndex.build(
        chunk_store_dir=chunk_store_dir,
        model_name=model_name,
        batch_size=batch_size,
        progress_callback=progress_callback,
    )

    # Always print the final count, even if the last callback happened
    # less than two seconds before completion.
    elapsed = time.monotonic() - start

    print()
    print(
        f"FAISS index built successfully: "
        f"{index.size:,} chunks "
        f"in {elapsed / 60:.1f} min"
    )
    print(f"Vector dimension : {index.dimension}")
    print(f"Embedding model  : {index.model_name}")
    print(f"Output directory  : {index_dir}")

    index.save(
        index_dir=index_dir,
    )

    print("FAISS index saved successfully.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point."""

    parser = argparse.ArgumentParser(
        description=(
            "Build the MIL-EVID BM25 and FAISS retrieval indexes "
            "from the local chunk store."
        )
    )

    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force rebuilding existing indexes.",
    )

    parser.add_argument(
        "--only",
        choices=["bm25", "faiss"],
        default=None,
        help="Build only the selected index.",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=EMBEDDING_BATCH_SIZE,
        help=(
            "Embedding batch size for FAISS. "
            f"Default: {EMBEDDING_BATCH_SIZE}."
        ),
    )

    args = parser.parse_args()

    if args.batch_size <= 0:
        parser.error("--batch-size must be greater than 0")

    settings = get_settings()

    configure_logging(
        settings.log_level,
    )

    chunk_store_dir = (
        BASE_DIR / settings.chunk_store_dir
    )

    bm25_dir = (
        BASE_DIR / settings.bm25_index_dir
    )

    faiss_dir = (
        BASE_DIR / settings.faiss_index_dir
    )

    if not chunk_store_dir.exists():
        raise SystemExit(
            f"Chunk store does not exist: {chunk_store_dir}"
        )

    print("=" * 70)
    print("MIL-EVID Phase 7: Building Retrieval Indexes")
    print("=" * 70)
    print(f"Chunk store      : {chunk_store_dir}")
    print(f"BM25 index dir   : {bm25_dir}")
    print(f"FAISS index dir  : {faiss_dir}")
    print(f"Embedding model  : {settings.embedding_model}")
    print(f"FAISS batch size : {args.batch_size}")
    print("=" * 70)

    if args.only in (None, "bm25"):
        build_bm25(
            chunk_store_dir=chunk_store_dir,
            index_dir=bm25_dir,
            rebuild=args.rebuild,
        )

    if args.only in (None, "faiss"):
        build_faiss(
            chunk_store_dir=chunk_store_dir,
            index_dir=faiss_dir,
            model_name=settings.embedding_model,
            rebuild=args.rebuild,
            batch_size=args.batch_size,
        )

    print()
    print("=" * 70)
    print("Index build complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()