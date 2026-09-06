"""Low-level, dependency-free text utilities.

These are pure functions with no knowledge of `EvidenceDocument` or
any other domain type — they operate on plain strings so they can be
unit tested in isolation and reused by both the cleaner and the
chunker without either depending on the other.

Sentence splitting here is a lightweight regex-based heuristic, not a
full NLP sentence tokenizer. That's a deliberate scope choice: pulling
in spaCy/nltk for sentence boundaries would be a heavy dependency for
a research prototype, and the heuristic is good enough for the
chunker's job (avoid splitting *inside* a sentence "where practical"),
which doesn't require perfect linguistic accuracy.
"""

from __future__ import annotations

import re
import unicodedata

# Matches whitespace runs (spaces, tabs, newlines) for collapsing.
_WHITESPACE_RE = re.compile(r"\s+")

# Matches Unicode control characters (category "C*") except the ones
# we want to keep as meaningful whitespace (\n, \t), which are handled
# separately by whitespace collapsing.
_CONTROL_CHAR_RE = re.compile(
    "[" + "".join(chr(c) for c in range(0x00, 0x20) if chr(c) not in "\n\t") + "]"
)

# Sentence boundary heuristic: split after ., !, or ? followed by
# whitespace and an uppercase letter/digit/quote, but not after common
# abbreviations. This intentionally stays simple; it is a heuristic,
# not a guarantee.
_ABBREVIATIONS = {
    "mr.", "mrs.", "ms.", "dr.", "prof.", "sr.", "jr.", "st.",
    "vs.", "etc.", "e.g.", "i.e.", "no.", "col.", "gen.", "lt.",
    "capt.", "maj.", "sgt.", "u.s.", "u.n.", "u.k.",
}
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")


def normalize_unicode(text: str) -> str:
    """Normalize Unicode to NFKC form.

    Collapses visually-identical but differently-encoded characters
    (e.g. full-width vs half-width digits, combining accents) so
    downstream deduplication and retrieval aren't fooled by encoding
    differences.
    """
    return unicodedata.normalize("NFKC", text)


def strip_control_characters(text: str) -> str:
    """Remove non-printable control characters, keeping newlines/tabs."""
    return _CONTROL_CHAR_RE.sub("", text)


def collapse_whitespace(text: str) -> str:
    """Collapse any run of whitespace into a single space and strip ends."""
    return _WHITESPACE_RE.sub(" ", text).strip()


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences using a lightweight heuristic.

    Not a substitute for a real NLP sentence tokenizer, but sufficient
    for chunk-boundary decisions. Falls back to returning the whole
    text as one "sentence" if no clear boundaries are found.
    """
    text = text.strip()
    if not text:
        return []

    raw_sentences = _SENTENCE_SPLIT_RE.split(text)

    # Re-merge any split that happened right after a known abbreviation
    # (e.g. "U.S. forces" should not be split into "U.S." / "forces").
    sentences: list[str] = []
    for piece in raw_sentences:
        if (
            sentences
            and sentences[-1].strip().lower().rsplit(" ", 1)[-1] in _ABBREVIATIONS
        ):
            sentences[-1] = f"{sentences[-1]} {piece}"
        else:
            sentences.append(piece)

    return [s.strip() for s in sentences if s.strip()]


def word_shingles(text: str, shingle_size: int) -> frozenset[str]:
    """Return the set of word n-grams ("shingles") for near-duplicate detection.

    Uses a lowercased, whitespace-tokenized word sequence. Returns an
    empty set for texts shorter than `shingle_size` words, since no
    complete shingle can be formed.
    """
    words = text.lower().split()
    if len(words) < shingle_size:
        return frozenset()
    return frozenset(
        " ".join(words[i : i + shingle_size])
        for i in range(len(words) - shingle_size + 1)
    )


def jaccard_similarity(a: frozenset[str], b: frozenset[str]) -> float:
    """Jaccard similarity between two shingle sets; 0.0 if both are empty."""
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)
