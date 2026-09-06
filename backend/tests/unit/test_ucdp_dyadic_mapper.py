from __future__ import annotations

from datetime import datetime

from app.domain.enums import Perspective, SourceType
from app.modules.ingestion.ucdp_dyadic_mapper import (
    map_ucdp_dyadic_record,
)


def make_record() -> dict[str, str]:
    return {
        "dyad_id": "399",
        "conflict_id": "200",
        "location": "Bolivia",
        "side_a": "Government of Bolivia",
        "side_a_id": "23",
        "side_a_2nd": "",
        "side_b": "Popular Revolutionary Movement",
        "side_b_id": "719",
        "side_b_2nd": "",
        "incompatibility": "2",
        "territory_name": "",
        "year": "1946",
        "intensity_level": "2",
        "type_of_conflict": "3",
        "start_date": "1946-07-18",
        "start_prec": "1",
        "start_date2": "1946-07-21",
        "start_prec2": "2",
        "gwno_a": "145",
        "gwno_a_2nd": "",
        "gwno_b": "",
        "gwno_b_2nd": "",
        "gwno_loc": "145",
        "region": "5",
        "version": "26.1",
    }


def test_maps_valid_dyadic_record() -> None:
    document = map_ucdp_dyadic_record(make_record())

    assert document is not None

    assert document.id == "ucdp-dyadic-399-1946"
    assert document.document_id == "ucdp-dyadic-399-1946"
    assert document.chunk_index == 0

    assert document.source == "UCDP Dyadic"
    assert document.source_type == SourceType.UCDP
    assert document.perspective == Perspective.HISTORICAL

    assert document.title == "Bolivia"

    assert document.date is not None
    assert isinstance(document.date, datetime)
    assert document.date.year == 1946
    assert document.date.month == 7
    assert document.date.day == 18


def test_generated_text_contains_core_conflict_information() -> None:
    document = map_ucdp_dyadic_record(make_record())

    assert document is not None

    assert "Government of Bolivia" in document.text
    assert "Popular Revolutionary Movement" in document.text
    assert "Bolivia" in document.text
    assert "1946" in document.text


def test_metadata_preserves_structured_dyadic_fields() -> None:
    document = map_ucdp_dyadic_record(make_record())

    assert document is not None

    assert document.metadata["dataset"] == "Dyadic"
    assert document.metadata["dyad_id"] == 399
    assert document.metadata["conflict_id"] == 200
    assert document.metadata["location"] == "Bolivia"
    assert document.metadata["side_a"] == "Government of Bolivia"
    assert (
        document.metadata["side_b"]
        == "Popular Revolutionary Movement"
    )
    assert document.metadata["year"] == 1946
    assert document.metadata["intensity_level"] == 2
    assert document.metadata["type_of_conflict"] == 3


def test_returns_none_when_dyad_id_is_missing() -> None:
    record = make_record()
    record["dyad_id"] = ""

    document = map_ucdp_dyadic_record(record)

    assert document is None


def test_does_not_mutate_input_record() -> None:
    record = make_record()
    original_record = dict(record)

    map_ucdp_dyadic_record(record)

    assert record == original_record


def test_removes_missing_values_from_metadata() -> None:
    record = make_record()

    document = map_ucdp_dyadic_record(record)

    assert document is not None

    assert "side_a_2nd" not in document.metadata
    assert "territory_name" not in document.metadata
    assert "gwno_b" not in document.metadata


def test_handles_missing_optional_fields() -> None:
    record = make_record()

    record["location"] = ""
    record["side_b"] = ""
    record["start_date"] = ""
    record["start_date2"] = ""

    document = map_ucdp_dyadic_record(record)

    assert document is not None

    assert document.id == "ucdp-dyadic-399-1946"
    assert document.document_id == "ucdp-dyadic-399-1946"
    assert document.date is not None
    assert document.date.year == 1946
    assert document.date.month == 1
    assert document.date.day == 1


def test_uses_year_when_start_date_is_missing() -> None:
    record = make_record()
    record["start_date"] = ""

    document = map_ucdp_dyadic_record(record)

    assert document is not None

    assert document.date is not None
    assert document.date.year == 1946
    assert document.date.month == 1
    assert document.date.day == 1