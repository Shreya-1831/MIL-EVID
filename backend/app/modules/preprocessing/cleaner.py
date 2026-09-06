"""Text cleaning.

Removes encoding noise and control characters, and collapses
whitespace, without altering the semantic content of the text. This
runs *before* chunking and deduplication so both operate on
consistently-formatted text.

All functions here are pure: they return new values and never mutate
their arguments, in line with the project-wide "do not mutate input
objects" requirement.
"""

from __future__ import annotations

from app.domain.models.evidence import EvidenceDocument
from app.utils.text import (
    collapse_whitespace,
    normalize_unicode,
    strip_control_characters,
)


def clean_text(raw_text: str) -> str:
    """Clean a raw text string for downstream processing.

    Pipeline: Unicode normalization -> control character stripping ->
    whitespace collapsing. Order matters: normalizing Unicode first
    ensures control-character stripping sees a canonical form.
    """
    text = normalize_unicode(raw_text)
    text = strip_control_characters(text)
    text = collapse_whitespace(text)
    return text


def clean_evidence_document(document: EvidenceDocument) -> EvidenceDocument:
    """Return a new `EvidenceDocument` with cleaned `text` and `title`.

    Does not touch `metadata`, `url`, `date`, or other fields — those
    are the normalizer's responsibility (see `normalizer.py`), keeping
    each preprocessing step focused on one concern.
    """
    cleaned_title = clean_text(document.title) if document.title else document.title
    return document.model_copy(
        update={
            "text": clean_text(document.text),
            "title": cleaned_title,
        }
    )
