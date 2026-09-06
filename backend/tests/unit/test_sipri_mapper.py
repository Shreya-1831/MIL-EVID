from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.domain.enums import Perspective, SourceType
from app.modules.ingestion.sipri_mapper import map_sipri_record


@pytest.fixture
def sipri_record() -> dict[str, str]:
    return {
        "Recipient": "India",
        "Supplier": "Russia",
        "Year of order": "2019",
        "Number ordered": "16",
        "Weapon designation": "RBU-6000",
        "Weapon description": "anti-submarine rocket launcher",
        "Deliveries in the Year Range": "0",
        "Year(s) of delivery": "",
        "status": "New",
        "Comments": (
            "For 16 ASW-SWC corvettes produced in India."
        ),
        "SIPRI TIV per unit": "3.5",
        "SIPRI TIV for total order": "56",
        "SIPRI TIV of delivered weapons": "0",
    }


def test_map_sipri_record_returns_evidence_document(
    sipri_record: dict[str, str],
) -> None:
    document = map_sipri_record(sipri_record)

    assert document.source == "SIPRI Arms Transfers Database"
    assert document.source_type == SourceType.SIPRI
    assert document.perspective == Perspective.MILITARY
    assert document.chunk_index == 0

    assert document.id.endswith("::chunk-0000")
    assert document.document_id.startswith("sipri-")


def test_map_sipri_record_builds_readable_text(
    sipri_record: dict[str, str],
) -> None:
    document = map_sipri_record(sipri_record)

    assert "India" in document.text
    assert "Russia" in document.text
    assert "RBU-6000" in document.text
    assert "16" in document.text
    assert "2019" in document.text
    assert "anti-submarine rocket launcher" in document.text


def test_map_sipri_record_preserves_metadata(
    sipri_record: dict[str, str],
) -> None:
    document = map_sipri_record(sipri_record)

    assert document.metadata["recipient"] == "India"
    assert document.metadata["supplier"] == "Russia"
    assert document.metadata["year_of_order"] == "2019"
    assert document.metadata["number_ordered"] == "16"
    assert document.metadata["weapon_designation"] == "RBU-6000"
    assert (
        document.metadata["weapon_description"]
        == "anti-submarine rocket launcher"
    )
    assert document.metadata["status"] == "New"
    assert document.metadata["sipri_tiv_per_unit"] == "3.5"


def test_map_sipri_record_generates_deterministic_id(
    sipri_record: dict[str, str],
) -> None:
    first = map_sipri_record(sipri_record)
    second = map_sipri_record(sipri_record)

    assert first.id == second.id
    assert first.document_id == second.document_id


def test_map_sipri_record_parses_order_year(
    sipri_record: dict[str, str],
) -> None:
    document = map_sipri_record(sipri_record)

    assert document.date == datetime(
        2019,
        1,
        1,
        tzinfo=timezone.utc,
    )


def test_map_sipri_record_handles_missing_optional_values() -> None:
    record = {
        "Recipient": "India",
        "Supplier": "Russia",
        "Weapon designation": "Test System",
    }

    document = map_sipri_record(record)

    assert document.text
    assert document.date is None
    assert document.metadata["recipient"] == "India"
    assert document.metadata["supplier"] == "Russia"
    assert document.metadata["weapon_designation"] == "Test System"

    assert "year_of_order" not in document.metadata
    assert "comments" not in document.metadata


def test_map_sipri_record_rejects_empty_record() -> None:
    with pytest.raises(ValueError):
        map_sipri_record({})