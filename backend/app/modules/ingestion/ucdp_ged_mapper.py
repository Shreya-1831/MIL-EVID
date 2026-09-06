"""Mapper for UCDP Georeferenced Event Dataset (GED) records.

Converts one raw GED CSV record into an EvidenceDocument suitable for
the evidence ingestion pipeline.

GED records are structured event data rather than natural-language
documents, so the mapper creates a concise factual evidence text from
the most relevant event fields while preserving the original structured
values in metadata.

The mapper is pure and does not mutate the input record.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.domain.enums import Perspective, SourceType
from app.domain.models.evidence import EvidenceDocument
from app.modules.preprocessing.normalizer import normalize_date


SOURCE_NAME = "UCDP GED"


def _clean_value(value: Any) -> str | None:
    """Return a stripped string value, or None for missing values."""

    if value is None:
        return None

    cleaned = str(value).strip()

    if not cleaned:
        return None

    return cleaned


def _parse_int(value: Any) -> int | None:
    """Best-effort conversion of a raw value to int."""

    if value is None:
        return None

    if isinstance(value, bool):
        return int(value)

    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _build_event_text(
    *,
    conflict_name: str | None,
    side_a: str | None,
    side_b: str | None,
    country: str | None,
    location: str | None,
    event_date: str | None,
    fatalities: int | None,
    source_article: str | None,
) -> str:
    """Build a readable factual description of one GED event."""

    parts: list[str] = []

    if conflict_name:
        parts.append(f"Conflict: {conflict_name}.")

    if side_a and side_b:
        parts.append(f"The event involved {side_a} and {side_b}.")
    elif side_a:
        parts.append(f"The event involved {side_a}.")
    elif side_b:
        parts.append(f"The event involved {side_b}.")

    if location and country:
        parts.append(f"The event occurred in {location}, {country}.")
    elif location:
        parts.append(f"The event occurred in {location}.")
    elif country:
        parts.append(f"The event occurred in {country}.")

    if event_date:
        parts.append(f"Event date: {event_date}.")

    if fatalities is not None:
        parts.append(f"Reported best estimate of fatalities: {fatalities}.")

    if source_article:
        parts.append(f"Source record: {source_article}")

    return " ".join(parts)


def map_ucdp_ged_record(
    record: Mapping[str, Any],
) -> EvidenceDocument | None:
    """Convert one UCDP GED CSV record into an EvidenceDocument.

    Returns None when the record does not contain a usable GED event ID
    or when no meaningful evidence text can be constructed.
    """

    event_id = _clean_value(record.get("id"))

    if event_id is None:
        return None

    conflict_name = _clean_value(record.get("conflict_name"))
    side_a = _clean_value(record.get("side_a"))
    side_b = _clean_value(record.get("side_b"))
    country = _clean_value(record.get("country"))
    location = _clean_value(record.get("where_description"))
    event_date_raw = _clean_value(record.get("date_start"))
    source_article = _clean_value(record.get("source_article"))

    best_fatalities = _parse_int(record.get("best"))
    high_fatalities = _parse_int(record.get("high"))
    low_fatalities = _parse_int(record.get("low"))

    text = _build_event_text(
        conflict_name=conflict_name,
        side_a=side_a,
        side_b=side_b,
        country=country,
        location=location,
        event_date=event_date_raw,
        fatalities=best_fatalities,
        source_article=source_article,
    )

    if not text:
        return None

    title = (
        conflict_name
        or f"UCDP GED Event {event_id}"
    )

    metadata = {
        "dataset": "GED",
        "ucdp_event_id": event_id,
        "relid": _clean_value(record.get("relid")),
        "year": _parse_int(record.get("year")),
        "active_year": _clean_value(record.get("active_year")),
        "code_status": _clean_value(record.get("code_status")),
        "type_of_violence": _parse_int(record.get("type_of_violence")),
        "conflict_dset_id": _parse_int(record.get("conflict_dset_id")),
        "conflict_new_id": _parse_int(record.get("conflict_new_id")),
        "conflict_name": conflict_name,
        "dyad_dset_id": _parse_int(record.get("dyad_dset_id")),
        "dyad_new_id": _parse_int(record.get("dyad_new_id")),
        "dyad_name": _clean_value(record.get("dyad_name")),
        "side_a": side_a,
        "side_b": side_b,
        "number_of_sources": _parse_int(record.get("number_of_sources")),
        "source_article": source_article,
        "source_office": _clean_value(record.get("source_office")),
        "source_date": _clean_value(record.get("source_date")),
        "source_headline": _clean_value(record.get("source_headline")),
        "where_description": location,
        "adm_1": _clean_value(record.get("adm_1")),
        "adm_2": _clean_value(record.get("adm_2")),
        "country": country,
        "region": _clean_value(record.get("region")),
        "event_clarity": _parse_int(record.get("event_clarity")),
        "date_start": event_date_raw,
        "date_end": _clean_value(record.get("date_end")),
        "deaths_a": _parse_int(record.get("deaths_a")),
        "deaths_b": _parse_int(record.get("deaths_b")),
        "deaths_civilians": _parse_int(
            record.get("deaths_civilians")
        ),
        "deaths_unknown": _parse_int(
            record.get("deaths_unknown")
        ),
        "best": best_fatalities,
        "high": high_fatalities,
        "low": low_fatalities,
        "latitude": _clean_value(record.get("latitude")),
        "longitude": _clean_value(record.get("longitude")),
    }

    cleaned_metadata = {
        key: value
        for key, value in metadata.items()
        if value is not None
    }

    return EvidenceDocument(
        id=f"ucdp-ged-{event_id}",
        document_id=f"ucdp-ged-{event_id}",
        chunk_index=0,
        text=text,
        source=SOURCE_NAME,
        source_type=SourceType.UCDP,
        perspective=Perspective.HISTORICAL,
        title=title,
        date=normalize_date(event_date_raw),
        url=None,
        page_number=None,
        metadata=cleaned_metadata,
    )