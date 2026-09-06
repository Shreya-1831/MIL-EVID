"""Duplicate detection and removal.

Two kinds of duplication are handled, deliberately kept separate:

1. **Exact duplicates** — identical (or whitespace/case-identical)
   text, typically from the same source being ingested twice, or
   mirrored across sources. Detected via a content hash; O(n).

2. **Near duplicates** — substantially overlapping but not identical
   text (e.g. a wire-service report syndicated with minor edits).
   Detected via Jaccard similarity over word shingles.

Near-duplicate detection is inherently pairwise, but a full O(n^2)
scan is avoided by only comparing documents whose lengths are within
a reasonable ratio of each other — two texts that differ greatly in
length cannot have high shingle overlap. This is a cheap, deterministic
pre-filter appropriate for the corpus sizes of a research prototype;
it does not require an embedding model or clustering step.

All functions are pure and return new tuples; inputs are never
mutated or reordered beyond removing the flagged items.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

from app.domain.models.evidence import EvidenceDocument
from app.utils.text import jaccard_similarity, word_shingles


def compute_content_hash(text: str) -> str:
    """Deterministic hash of normalized text content.

    Used as the exact-duplicate key. Normalizes case and whitespace
    before hashing so trivial formatting differences don't prevent
    two otherwise-identical documents from being recognized as
    duplicates.
    """
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def remove_exact_duplicates(
    documents: Sequence[EvidenceDocument],
) -> tuple[EvidenceDocument, ...]:
    """Remove exact (post-normalization) duplicate documents.

    Keeps the first occurrence of each distinct content hash, in
    input order, so results are deterministic regardless of which
    duplicate happens to be "better" — callers that care about
    preferring one source over another should deduplicate per-source
    before merging document lists.
    """
    seen_hashes: set[str] = set()
    kept: list[EvidenceDocument] = []
    for document in documents:
        content_hash = compute_content_hash(document.text)
        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)
        kept.append(document)
    return tuple(kept)


def find_near_duplicate_pairs(
    documents: Sequence[EvidenceDocument],
    *,
    threshold: float,
    shingle_size: int,
    length_ratio_cutoff: float = 0.5,
) -> tuple[tuple[str, str, float], ...]:
    """Find pairs of documents whose text is near-duplicate.

    Returns `(document_id_a, document_id_b, similarity)` tuples for
    every pair scoring at or above `threshold`, sorted by descending
    similarity then by document ID for determinism.

    `length_ratio_cutoff` skips shingle computation for pairs whose
    text lengths differ too much to plausibly reach `threshold`
    similarity — a cheap guard against wasted work, not a full index
    structure (appropriate for prototype-scale corpora; a production
    system would use MinHash/LSH bucketing instead).
    """
    shingles = [word_shingles(doc.text, shingle_size) for doc in documents]
    lengths = [len(doc.text) for doc in documents]

    results: list[tuple[str, str, float]] = []
    n = len(documents)
    for i in range(n):
        if not shingles[i]:
            continue
        for j in range(i + 1, n):
            if not shingles[j]:
                continue
            shorter, longer = sorted((lengths[i], lengths[j]))
            if longer == 0 or shorter / longer < length_ratio_cutoff:
                continue
            similarity = jaccard_similarity(shingles[i], shingles[j])
            if similarity >= threshold:
                pair = tuple(sorted((documents[i].id, documents[j].id)))
                results.append((pair[0], pair[1], similarity))

    return tuple(sorted(results, key=lambda item: (-item[2], item[0], item[1])))


def remove_near_duplicates(
    documents: Sequence[EvidenceDocument],
    *,
    threshold: float,
    shingle_size: int,
) -> tuple[EvidenceDocument, ...]:
    """Greedily remove near-duplicate documents, keeping the first seen.

    For each document, if it is near-duplicate with any document
    already kept, it is dropped; otherwise it is kept. Processing
    follows input order, so results are deterministic and the "first"
    copy of a duplicated story is the one retained.
    """
    if not documents:
        return ()

    kept: list[EvidenceDocument] = []
    kept_shingles: list[frozenset[str]] = []

    for document in documents:
        doc_shingles = word_shingles(document.text, shingle_size)
        is_duplicate = False
        if doc_shingles:
            for existing_shingles in kept_shingles:
                if jaccard_similarity(doc_shingles, existing_shingles) >= threshold:
                    is_duplicate = True
                    break
        if not is_duplicate:
            kept.append(document)
            kept_shingles.append(doc_shingles)

    return tuple(kept)
