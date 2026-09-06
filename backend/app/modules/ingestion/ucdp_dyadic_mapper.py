from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.domain.enums import Perspective, SourceType
from app.domain.models.evidence import EvidenceDocument


def map_ucdp_dyadic_record(
    record: dict[str, Any],
) -> EvidenceDocument | None:
    """Convert one UCDP Dyadic dataset record into an EvidenceDocument."""

    dyad_id = _get_string(record, "dyad_id")

    if not dyad_id:
        return None

    year = _get_int(record, "year")

    document_id = _build_document_id(
        dyad_id=dyad_id,
        year=year,
    )

    date = _parse_date(
        _get_string(record, "start_date")
    )

    if date is None and year is not None:
        date = datetime(
            year,
            1,
            1,
            tzinfo=timezone.utc,
        )

    metadata = _build_metadata(record)

    return EvidenceDocument(
        id=document_id,
        document_id=document_id,
        chunk_index=0,
        text=_build_text(record),
        source="UCDP Dyadic",
        source_type=SourceType.UCDP,
        perspective=Perspective.HISTORICAL,
        title=_get_string(record, "location"),
        date=date,
        url=None,
        page_number=None,
        metadata=metadata,
    )


def _build_document_id(
    *,
    dyad_id: str,
    year: int | None,
) -> str:
    """Build a stable identifier for a UCDP Dyadic record."""

    if year is None:
        return f"ucdp-dyadic-{dyad_id}"

    return f"ucdp-dyadic-{dyad_id}-{year}"


def _build_text(
    record: dict[str, Any],
) -> str:
    """Create retrieval-friendly text from a dyadic conflict record."""

    parts: list[str] = []

    location = _get_string(record, "location")
    side_a = _get_string(record, "side_a")
    side_b = _get_string(record, "side_b")
    year = _get_string(record, "year")
    intensity_level = _get_string(record, "intensity_level")
    type_of_conflict = _get_string(record, "type_of_conflict")
    incompatibility = _get_string(record, "incompatibility")

    if side_a and side_b:
        parts.append(
            f"The conflict involved {side_a} and {side_b}."
        )
    elif side_a:
        parts.append(
            f"The conflict involved {side_a}."
        )
    elif side_b:
        parts.append(
            f"The conflict involved {side_b}."
        )

    if location:
        parts.append(
            f"The conflict was located in {location}."
        )

    if year:
        parts.append(
            f"The conflict record applies to the year {year}."
        )

    if intensity_level:
        parts.append(
            f"The recorded conflict intensity level was {intensity_level}."
        )

    if type_of_conflict:
        parts.append(
            f"The recorded conflict type was {type_of_conflict}."
        )

    if incompatibility:
        parts.append(
            f"The recorded incompatibility category was {incompatibility}."
        )

    return " ".join(parts)


def _build_metadata(
    record: dict[str, Any],
) -> dict[str, Any]:
    """Build metadata while removing missing values."""

    metadata: dict[str, Any] = {
        "dataset": "Dyadic",
        "dyad_id": _get_int(record, "dyad_id"),
        "conflict_id": _get_int(record, "conflict_id"),
        "location": _get_string(record, "location"),
        "side_a": _get_string(record, "side_a"),
        "side_a_id": _get_int(record, "side_a_id"),
        "side_a_2nd": _get_string(record, "side_a_2nd"),
        "side_b": _get_string(record, "side_b"),
        "side_b_id": _get_int(record, "side_b_id"),
        "side_b_2nd": _get_string(record, "side_b_2nd"),
        "incompatibility": _get_int(
            record,
            "incompatibility",
        ),
        "territory_name": _get_string(
            record,
            "territory_name",
        ),
        "year": _get_int(record, "year"),
        "intensity_level": _get_int(
            record,
            "intensity_level",
        ),
        "type_of_conflict": _get_int(
            record,
            "type_of_conflict",
        ),
        "start_date": _get_string(
            record,
            "start_date",
        ),
        "start_prec": _get_int(
            record,
            "start_prec",
        ),
        "start_date2": _get_string(
            record,
            "start_date2",
        ),
        "start_prec2": _get_int(
            record,
            "start_prec2",
        ),
        "gwno_a": _get_int(record, "gwno_a"),
        "gwno_a_2nd": _get_int(
            record,
            "gwno_a_2nd",
        ),
        "gwno_b": _get_int(record, "gwno_b"),
        "gwno_b_2nd": _get_int(
            record,
            "gwno_b_2nd",
        ),
        "gwno_loc": _get_int(record, "gwno_loc"),
        "region": _get_int(record, "region"),
        "version": _get_string(record, "version"),
    }

    return {
        key: value
        for key, value in metadata.items()
        if value is not None
    }


def _get_string(
    record: dict[str, Any],
    key: str,
) -> str | None:
    """Return a stripped string value or None."""

    value = record.get(key)

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return text


def _get_int(
    record: dict[str, Any],
    key: str,
) -> int | None:
    """Return an integer value or None."""

    value = _get_string(record, key)

    if value is None:
        return None

    try:
        return int(value)
    except ValueError:
        return None


def _parse_date(
    value: str | None,
) -> datetime | None:
    """Parse an ISO date string as a UTC datetime."""

    if value is None:
        return None

    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)