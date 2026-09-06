"""Context-preserving chunking.

Splits a cleaned, normalized `EvidenceDocument` into smaller
`EvidenceDocument` chunks suitable for embedding and retrieval, while
preserving all source metadata (title, url, date, source, source_type,
perspective) on every chunk — a retrieved chunk must be traceable back
to its full citation without a separate lookup.

Chunking is sentence-aware: it accumulates whole sentences up to
`chunk_size` characters rather than cutting at an arbitrary character
offset, per the "avoid splitting in the middle of sentences where
practical" requirement. A single sentence longer than `chunk_size` is
kept whole rather than force-split, since splitting it would produce a
fragment with no coherent meaning.

Chunk IDs are derived deterministically from the parent document ID
and chunk index (`"{parent_id}::chunk-{index:04d}"`), so re-running
chunking over the same input documents in the same order always
produces the same IDs — required for stable citations and for
BM25/FAISS index rebuilds to line up with unchanged database rows.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.core.exceptions import PreprocessingError
from app.domain.models.evidence import EvidenceDocument
from app.utils.text import split_into_sentences


def generate_chunk_id(parent_document_id: str, chunk_index: int) -> str:
    """Build a stable, human-readable chunk ID.

    Deliberately not content-hash-based: content hashing would make
    the ID change if the source text is re-cleaned with a slightly
    different normalization rule, which would needlessly invalidate
    citations and index entries. Index-based IDs are stable as long as
    chunking is deterministic, which it is (see module docstring).
    """
    if not parent_document_id:
        raise PreprocessingError("parent_document_id must not be empty")
    if chunk_index < 0:
        raise PreprocessingError("chunk_index must be non-negative")
    return f"{parent_document_id}::chunk-{chunk_index:04d}"


def chunk_text(text: str, *, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split `text` into chunks of at most ~`chunk_size` characters.

    Greedily accumulates sentences into the current chunk; when adding
    the next sentence would exceed `chunk_size`, the current chunk is
    closed and a new one is opened, seeded with trailing sentences
    from the closed chunk totalling up to `chunk_overlap` characters
    (for retrieval context continuity across chunk boundaries).

    A sentence longer than `chunk_size` on its own becomes its own
    chunk rather than being split mid-sentence.
    """
    if chunk_overlap >= chunk_size:
        raise PreprocessingError(
            f"chunk_overlap ({chunk_overlap}) must be smaller than "
            f"chunk_size ({chunk_size})"
        )

    sentences = split_into_sentences(text)
    if not sentences:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        if current and current_len + 1 + sentence_len > chunk_size:
            chunks.append(" ".join(current))

            # Seed the next chunk with trailing sentences from the
            # closed chunk, up to chunk_overlap characters, so
            # retrieval doesn't lose context right at the boundary.
            overlap_sentences: list[str] = []
            overlap_len = 0
            for prev_sentence in reversed(current):
                candidate_len = len(prev_sentence) + (1 if overlap_sentences else 0)
                if overlap_len + candidate_len > chunk_overlap:
                    break
                overlap_sentences.insert(0, prev_sentence)
                overlap_len += candidate_len

            current = overlap_sentences
            current_len = overlap_len

        current.append(sentence)
        current_len += sentence_len + (1 if len(current) > 1 else 0)

    if current:
        chunks.append(" ".join(current))

    return chunks


def chunk_document(
    document: EvidenceDocument,
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[EvidenceDocument, ...]:
    """Split one `EvidenceDocument` into chunk-level `EvidenceDocument`s.

    Every chunk preserves `source`, `source_type`, `perspective`,
    `title`, `date`, and `url` from the parent. `metadata` is copied
    and extended with `parent_document_id` and `chunk_index` so the
    relationship to the source document is always recoverable, and
    `created_at` is preserved as the parent's ingestion time rather
    than reset per chunk (the chunk was not created earlier than its
    parent).

    Does not mutate `document`; returns new instances only. If the
    document's text produces no sentences (e.g. empty after cleaning),
    returns an empty tuple rather than raising — an empty document is
    a data-quality issue for the caller to filter, not a chunking
    failure.
    """
    pieces = chunk_text(document.text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    chunks: list[EvidenceDocument] = []
    parent_document_id = document.document_id or document.id

    for index, piece in enumerate(pieces):
        chunk_metadata = dict(document.metadata)
        chunk_metadata["parent_document_id"] = parent_document_id
        chunk_metadata["chunk_index"] = index
        chunk_metadata["chunk_count"] = len(pieces)

        chunks.append(
            document.model_copy(
                update={
                    "id": generate_chunk_id(parent_document_id, index),
                    "document_id": parent_document_id,
                    "chunk_index": index,
                    "text": piece,
                    "metadata": chunk_metadata,
                }
            )
        )

    return tuple(chunks)


def chunk_documents(
    documents: Sequence[EvidenceDocument],
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[EvidenceDocument, ...]:
    """Chunk a sequence of documents, concatenating all resulting chunks."""
    all_chunks: list[EvidenceDocument] = []
    for document in documents:
        all_chunks.extend(
            chunk_document(document, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        )
    return tuple(all_chunks)
