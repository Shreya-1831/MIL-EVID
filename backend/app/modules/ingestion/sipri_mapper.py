"""Mapper for SIPRI Arms Transfers Database records.

Converts raw SIPRI CSV rows into EvidenceDocument instances.

Each SIPRI row represents an arms-transfer record. The mapper converts
the structured row into retrieval-friendly natural-language evidence
while preserving the original structured information in metadata.

This module is source-specific by design. It knows the SIPRI column
names and does not attempt to provide generic mapping behaviour.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from app.domain.enums import Perspective, SourceType
from app.domain.models.evidence import EvidenceDocument


def _clean_value(value: Any) -> str | None:
    """Return a stripped string value or None for missing values."""

    if value is None:
        return None

    cleaned = str(value).strip()

    if not cleaned or cleaned == "?":
        return None

    return cleaned


def _parse_year(value: Any) -> datetime | None:
    """Convert a SIPRI year value into a UTC datetime."""

    year = _clean_value(value)

    if year is None:
        return None

    try:
        return datetime(int(year), 1, 1, tzinfo=timezone.utc)
    except ValueError:
        return None


def _generate_document_id(row: dict[str, Any]) -> str:
    """Generate a deterministic ID for one SIPRI record."""

    identity_fields = (
        _clean_value(row.get("Recipient")) or "",
        _clean_value(row.get("Supplier")) or "",
        _clean_value(row.get("Year of order")) or "",
        _clean_value(row.get("Weapon designation")) or "",
        _clean_value(row.get("Weapon description")) or "",
    )

    identity = "|".join(identity_fields)

    digest = hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()[:16]

    return f"sipri-{digest}"


def _build_text(row: dict[str, Any]) -> str:
    """Build retrieval-friendly evidence text from a SIPRI row."""

    recipient = _clean_value(row.get("Recipient"))
    supplier = _clean_value(row.get("Supplier"))
    year_of_order = _clean_value(row.get("Year of order"))
    number_ordered = _clean_value(row.get("Number ordered"))
    weapon = _clean_value(row.get("Weapon designation"))
    description = _clean_value(row.get("Weapon description"))
    deliveries = _clean_value(
        row.get("Deliveries in the Year Range")
    )
    delivery_years = _clean_value(row.get("Year(s) of delivery"))
    status = _clean_value(row.get("status"))
    comments = _clean_value(row.get("Comments"))

    parts: list[str] = []

    main_parts: list[str] = []

    if recipient:
        main_parts.append(recipient)

    if number_ordered and weapon:
        main_parts.append(
            f"ordered {number_ordered} {weapon}"
        )
    elif weapon:
        main_parts.append(
            f"was associated with {weapon}"
        )

    if supplier:
        main_parts.append(f"from {supplier}")

    if year_of_order:
        main_parts.append(f"in {year_of_order}")

    if main_parts:
        parts.append(" ".join(main_parts) + ".")

    if description:
        parts.append(
            f"The weapon or system was described as {description}."
        )

    if deliveries:
        parts.append(
            f"Deliveries in the reported year range: {deliveries}."
        )

    if delivery_years:
        parts.append(
            f"Reported delivery years: {delivery_years}."
        )

    if status:
        parts.append(
            f"Status: {status}."
        )

    if comments:
        parts.append(comments)

    text = " ".join(parts).strip()

    if not text:
        raise ValueError(
            "SIPRI record does not contain enough information "
            "to build evidence text"
        )

    return text


def map_sipri_record(
    row: dict[str, Any],
) -> EvidenceDocument:
    """Convert one raw SIPRI CSV row into an EvidenceDocument."""

    document_id = _generate_document_id(row)

    text = _build_text(row)

    metadata = {
        "recipient": _clean_value(row.get("Recipient")),
        "supplier": _clean_value(row.get("Supplier")),
        "year_of_order": _clean_value(
            row.get("Year of order")
        ),
        "number_ordered": _clean_value(
            row.get("Number ordered")
        ),
        "weapon_designation": _clean_value(
            row.get("Weapon designation")
        ),
        "weapon_description": _clean_value(
            row.get("Weapon description")
        ),
        "deliveries_in_year_range": _clean_value(
            row.get("Deliveries in the Year Range")
        ),
        "delivery_years": _clean_value(
            row.get("Year(s) of delivery")
        ),
        "status": _clean_value(row.get("status")),
        "comments": _clean_value(row.get("Comments")),
        "sipri_tiv_per_unit": _clean_value(
            row.get("SIPRI TIV per unit")
        ),
        "sipri_tiv_total_order": _clean_value(
            row.get("SIPRI TIV for total order")
        ),
        "sipri_tiv_delivered": _clean_value(
            row.get("SIPRI TIV of delivered weapons")
        ),
    }

    metadata = {
        key: value
        for key, value in metadata.items()
        if value is not None
    }

    weapon = _clean_value(
        row.get("Weapon designation")
    )

    description = _clean_value(
        row.get("Weapon description")
    )

    title_parts = [
        part
        for part in (weapon, description)
        if part
    ]

    title = " - ".join(title_parts) or "SIPRI Arms Transfer Record"

    return EvidenceDocument(
        id=f"{document_id}::chunk-0000",
        document_id=document_id,
        chunk_index=0,
        text=text,
        source="SIPRI Arms Transfers Database",
        source_type=SourceType.SIPRI,
        perspective=Perspective.MILITARY,
        title=title,
        date=_parse_year(row.get("Year of order")),
        url=None,
        page_number=None,
        metadata=metadata,
    )