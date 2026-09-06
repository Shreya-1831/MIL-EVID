"""Metadata normalization.

Static sources (UCDP, ICRC, UN Peacemaker) and the dynamic ACLED feed
each represent dates, URLs, and metadata slightly differently. This
module normalizes all of that into the consistent shape
`EvidenceDocument` expects, so every downstream module (chunking,
retrieval, confidence scoring's "freshness" component) can rely on a
single representation instead of re-parsing source-specific formats.

Pure functions throughout; nothing here mutates its input.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.domain.models.evidence import EvidenceDocument
from app.utils.text import collapse_whitespace

# Date formats we accept from raw source records, tried in order.
# Extend this list as new source formats are encountered rather than
# writing a bespoke parser per source.
_KNOWN_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y/%m/%d",
    "%d %B %Y",
    "%d %b %Y",
    "%B %d, %Y",
    "%Y",
)

def normalize_date(raw: Any) -> datetime | None:
    """Best-effort parse of a source-provided date value into `datetime`.

    Accepts `datetime`, `date`, or a string in one of
    `_KNOWN_DATE_FORMATS`. Returns None (rather than raising) for
    anything unparseable — a missing/unparseable date should not abort
    ingestion of an otherwise-valid evidence item; downstream freshness
    scoring treats a None date as "unknown," not "invalid."
    """
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, date):
        return datetime(raw.year, raw.month, raw.day)
    if not isinstance(raw, str):
        return None

    candidate = raw.strip()
    if not candidate:
        return None

    for fmt in _KNOWN_DATE_FORMATS:
        try:
            return datetime.strptime(candidate, fmt)
        except ValueError:
            continue
    return None


def normalize_url(raw: str | None) -> str | None:
    """Trim and lightly validate a URL string.

    Does not perform network validation (out of scope for
    preprocessing) — only strips whitespace and rejects obviously
    non-URL values so bad data doesn't propagate into citations.
    """
    if raw is None:
        return None
    trimmed = raw.strip()
    if not trimmed:
        return None
    if not (trimmed.startswith("http://") or trimmed.startswith("https://")):
        return None
    return trimmed


def normalize_metadata(raw_metadata: dict[str, Any]) -> dict[str, Any]:
    """Normalize a free-form metadata dict.

    - Drops keys with None or empty-string values (nothing useful to
      store).
    - Collapses whitespace in string values.
    - Leaves non-string values (numbers, lists, nested dicts) as-is.

    Returns a new dict; does not mutate `raw_metadata`.
    """
    normalized: dict[str, Any] = {}
    for key, value in raw_metadata.items():
        if value is None:
            continue
        if isinstance(value, str):
            cleaned = collapse_whitespace(value)
            if not cleaned:
                continue
            normalized[key] = cleaned
        else:
            normalized[key] = value
    return normalized


def normalize_evidence_document(document: EvidenceDocument) -> EvidenceDocument:
    """Return a new `EvidenceDocument` with normalized date/url/metadata.

    `text` and `title` are left untouched here — that's `cleaner.py`'s
    responsibility. Callers typically apply `clean_evidence_document`
    and `normalize_evidence_document` in sequence (see
    `modules/preprocessing/__init__.py` usage in the pipeline).
    """
    normalized_date = (
        normalize_date(document.date) if document.date is not None else None
    )
    normalized_url = normalize_url(document.url)
    normalized_metadata = normalize_metadata(document.metadata)

    return document.model_copy(
        update={
            "date": normalized_date,
            "url": normalized_url,
            "metadata": normalized_metadata,
        }
    )
