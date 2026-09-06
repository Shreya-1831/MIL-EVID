from __future__ import annotations

from app.domain.enums import Perspective, SourceType
from app.modules.ingestion.ucdp_ged_mapper import map_ucdp_ged_record


def make_record() -> dict[str, str]:
    return {
        "id": "1568",
        "relid": "ALG-1992-1-1-6",
        "year": "1992",
        "active_year": "true",
        "code_status": "Clear",
        "type_of_violence": "1",
        "conflict_dset_id": "386",
        "conflict_new_id": "386",
        "conflict_name": "Algeria: Government",
        "dyad_dset_id": "828",
        "dyad_new_id": "828",
        "dyad_name": "Government of Algeria - AIS",
        "side_a": "Government of Algeria",
        "side_b": "AIS",
        "number_of_sources": "-1",
        "source_article": (
            "Reuters 3/19/1992 ALGERIAN SECURITY WARNS "
            "OF KILLING CAMPAIGN."
        ),
        "source_office": "",
        "source_date": "",
        "source_headline": "",
        "where_description": (
            "Medea town, Medea district, Medea province"
        ),
        "adm_1": "Medea province",
        "adm_2": "Medea commune",
        "latitude": "36.264169",
        "longitude": "2.753926",
        "country": "Algeria",
        "region": "Africa",
        "event_clarity": "1",
        "date_start": "1992-03-17 00:00:00.000",
        "date_end": "1992-03-17 00:00:00.000",
        "deaths_a": "1",
        "deaths_b": "0",
        "deaths_civilians": "1",
        "deaths_unknown": "0",
        "best": "2",
        "high": "2",
        "low": "2",
    }


def test_maps_valid_ged_record() -> None:
    document = map_ucdp_ged_record(make_record())

    assert document is not None

    assert document.id == "ucdp-ged-1568"
    assert document.document_id == "ucdp-ged-1568"
    assert document.chunk_index == 0

    assert document.source == "UCDP GED"
    assert document.source_type == SourceType.UCDP
    assert document.perspective == Perspective.HISTORICAL

    assert document.title == "Algeria: Government"

    assert document.date is not None
    assert document.date.year == 1992
    assert document.date.month == 3
    assert document.date.day == 17


def test_generated_text_contains_core_event_information() -> None:
    document = map_ucdp_ged_record(make_record())

    assert document is not None

    assert "Algeria: Government" in document.text
    assert "Government of Algeria" in document.text
    assert "AIS" in document.text
    assert "Medea town" in document.text
    assert "Algeria" in document.text
    assert "2" in document.text


def test_metadata_preserves_structured_ged_fields() -> None:
    document = map_ucdp_ged_record(make_record())

    assert document is not None

    assert document.metadata["dataset"] == "GED"
    assert document.metadata["ucdp_event_id"] == "1568"
    assert document.metadata["conflict_name"] == "Algeria: Government"
    assert document.metadata["side_a"] == "Government of Algeria"
    assert document.metadata["side_b"] == "AIS"
    assert document.metadata["country"] == "Algeria"
    assert document.metadata["best"] == 2
    assert document.metadata["high"] == 2
    assert document.metadata["low"] == 2


def test_returns_none_when_event_id_is_missing() -> None:
    record = make_record()
    record["id"] = ""

    document = map_ucdp_ged_record(record)

    assert document is None


def test_does_not_mutate_input_record() -> None:
    record = make_record()
    original_record = dict(record)

    map_ucdp_ged_record(record)

    assert record == original_record


def test_removes_missing_values_from_metadata() -> None:
    record = make_record()

    record["source_office"] = ""
    record["source_date"] = ""
    record["source_headline"] = ""

    document = map_ucdp_ged_record(record)

    assert document is not None

    assert "source_office" not in document.metadata
    assert "source_date" not in document.metadata
    assert "source_headline" not in document.metadata


def test_handles_missing_optional_fields() -> None:
    record = {
        "id": "9999",
        "conflict_name": "Test Conflict",
        "country": "Test Country",
        "date_start": "2020-01-01",
    }

    document = map_ucdp_ged_record(record)

    assert document is not None

    assert document.id == "ucdp-ged-9999"
    assert document.title == "Test Conflict"
    assert document.metadata["conflict_name"] == "Test Conflict"
    assert document.metadata["country"] == "Test Country"