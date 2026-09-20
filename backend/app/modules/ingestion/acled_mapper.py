"""Mapper for ACLED conflict-event records.

Converts one raw ACLED API event into an EvidenceDocument.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

from app.domain.enums import Perspective, SourceType
from app.domain.models.evidence import EvidenceDocument


SOURCE_NAME = "ACLED"


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


def _parse_date(value: Any) -> datetime | None:
    """Convert an ACLED event date into a datetime."""
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())

    try:
        return datetime.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        return None


def _build_event_text(
    *,
    event_date: str | None,
    event_type: str | None,
    sub_event_type: str | None,
    actor1: str | None,
    actor2: str | None,
    country: str | None,
    location: str | None,
    fatalities: int | None,
    notes: str | None,
) -> str:
    """Build a concise factual description of an ACLED event."""

    parts: list[str] = []

    if event_date:
        parts.append(f"Event date: {event_date}.")

    if event_type:
        parts.append(f"Event type: {event_type}.")

    if sub_event_type:
        parts.append(f"Sub-event type: {sub_event_type}.")

    if actor1 and actor2:
        parts.append(f"The event involved {actor1} and {actor2}.")
    elif actor1:
        parts.append(f"The event involved {actor1}.")
    elif actor2:
        parts.append(f"The event involved {actor2}.")

    if location and country:
        parts.append(f"The event occurred in {location}, {country}.")
    elif location:
        parts.append(f"The event occurred in {location}.")
    elif country:
        parts.append(f"The event occurred in {country}.")

    if fatalities is not None:
        parts.append(f"Reported fatalities: {fatalities}.")

    if notes:
        parts.append(f"ACLED report: {notes}")

    return " ".join(parts)


def map_acled_event(
    record: Mapping[str, Any],
) -> EvidenceDocument | None:
    """Convert one ACLED API event into an EvidenceDocument."""

    event_id = _clean_value(record.get("event_id_cnty"))

    if event_id is None:
        return None

    event_date_raw = _clean_value(record.get("event_date"))
    event_type = _clean_value(record.get("event_type"))
    sub_event_type = _clean_value(record.get("sub_event_type"))
    actor1 = _clean_value(record.get("actor1"))
    actor2 = _clean_value(record.get("actor2"))
    country = _clean_value(record.get("country"))
    location = _clean_value(record.get("location"))
    notes = _clean_value(record.get("notes"))
    fatalities = _parse_int(record.get("fatalities"))

    text = _build_event_text(
        event_date=event_date_raw,
        event_type=event_type,
        sub_event_type=sub_event_type,
        actor1=actor1,
        actor2=actor2,
        country=country,
        location=location,
        fatalities=fatalities,
        notes=notes,
    )

    if not text:
        return None

    metadata = {
        "dataset": "ACLED",
        "acled_event_id": event_id,
        "event_id_cnty": event_id,
        "event_date": event_date_raw,
        "year": _parse_int(record.get("year")),
        "time_precision": _parse_int(record.get("time_precision")),
        "disorder_type": _clean_value(record.get("disorder_type")),
        "event_type": event_type,
        "sub_event_type": sub_event_type,
        "actor1": actor1,
        "assoc_actor_1": _clean_value(record.get("assoc_actor_1")),
        "inter1": _clean_value(record.get("inter1")),
        "actor2": actor2,
        "assoc_actor_2": _clean_value(record.get("assoc_actor_2")),
        "inter2": _clean_value(record.get("inter2")),
        "interaction": _clean_value(record.get("interaction")),
        "civilian_targeting": _clean_value(
            record.get("civilian_targeting")
        ),
        "iso": _parse_int(record.get("iso")),
        "region": _clean_value(record.get("region")),
        "country": country,
        "admin1": _clean_value(record.get("admin1")),
        "admin2": _clean_value(record.get("admin2")),
        "admin3": _clean_value(record.get("admin3")),
        "location": location,
        "latitude": _clean_value(record.get("latitude")),
        "longitude": _clean_value(record.get("longitude")),
        "geo_precision": _parse_int(record.get("geo_precision")),
        "source": _clean_value(record.get("source")),
        "source_scale": _clean_value(record.get("source_scale")),
        "fatalities": fatalities,
        "timestamp": record.get("timestamp"),
    }

    cleaned_metadata = {
        key: value
        for key, value in metadata.items()
        if value is not None
    }

    title = (
        f"{event_type} — {location}"
        if event_type and location
        else f"ACLED Event {event_id}"
    )

    return EvidenceDocument(
        id=f"acled-{event_id}",
        document_id=f"acled-{event_id}",
        chunk_index=0,
        text=text,
        source=SOURCE_NAME,
        source_type=SourceType.ACLED,
        perspective=Perspective.MILITARY,
        title=title,
        date=_parse_date(event_date_raw),
        url=None,
        page_number=None,
        metadata=cleaned_metadata,
    )