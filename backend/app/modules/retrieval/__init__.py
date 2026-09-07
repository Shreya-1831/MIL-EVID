"""Phase 7: embedding & index generation.

This package builds and serves the two retrieval indexes MIL-EVID
uses over evidence chunks:

- `bm25_index`: sparse keyword search (rank-bm25) over chunk text.
- `embedding_model` / `faiss_index`: dense semantic search (Sentence
  Transformers + FAISS) over the same chunk text.

Both indexes are built directly from the local JSONL chunk store
(`app.repositories.chunk_file_store`), map results back to chunk IDs,
and are persisted under the directories configured in
`app.core.config.Settings` (`bm25_index_dir` / `faiss_index_dir`).
Neither index stores full chunk text; the JSONL files remain the
single source of truth for text, matching the rest of the codebase.

Combining the two (hybrid retrieval / RRF / reranking) is out of
scope for this package and belongs to a later phase.
"""

from __future__ import annotations

from app.modules.retrieval.bm25_index import BM25Index, BM25SearchResult, tokenize
from app.modules.retrieval.embedding_model import embed_texts, get_embedding_model
from app.modules.retrieval.faiss_index import DenseSearchResult, FaissIndex

__all__ = [
    "BM25Index",
    "BM25SearchResult",
    "tokenize",
    "embed_texts",
    "get_embedding_model",
    "DenseSearchResult",
    "FaissIndex",
]
