from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import Mock

from app.domain.enums import Perspective, SourceType
from app.domain.models.evidence import EvidenceDocument
from app.modules.ingestion.static_ingestion import (
    ingest_csv_file,
)


def make_document(
    *,
    document_id: str = "test-001",
) -> EvidenceDocument:
    return EvidenceDocument(
        id=document_id,
        document_id=document_id,
        chunk_index=0,
        text="Test evidence text.",
        source="Test Source",
        source_type=SourceType.UCDP,
        perspective=Perspective.HISTORICAL,
        title="Test Evidence",
        date=None,
        url=None,
        page_number=None,
        metadata={},
    )


def write_csv(
    path: Path,
    rows: list[dict[str, str]],
) -> None:
    fieldnames = list(rows[0].keys())

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


def test_ingest_csv_file_maps_and_ingests_documents(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "test.csv"

    write_csv(
        csv_path,
        [
            {"id": "1", "text": "First record"},
            {"id": "2", "text": "Second record"},
        ],
    )

    first_document = make_document(
        document_id="doc-001",
    )
    second_document = make_document(
        document_id="doc-002",
    )

    mapper = Mock(
        side_effect=[
            first_document,
            second_document,
        ]
    )

    ingestion_service = Mock()
    ingestion_service.ingest.return_value = (
        first_document,
        second_document,
    )

    results = ingest_csv_file(
        csv_path=csv_path,
        mapper=mapper,
        ingestion_service=ingestion_service,
    )

    assert results == (
        first_document,
        second_document,
    )

    assert mapper.call_count == 2

    ingestion_service.ingest.assert_called_once_with(
        (
            first_document,
            second_document,
        )
    )


def test_ingest_csv_file_skips_records_mapper_rejects(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "test.csv"

    write_csv(
        csv_path,
        [
            {"id": "1", "text": "Valid"},
            {"id": "", "text": "Invalid"},
        ],
    )

    document = make_document()

    mapper = Mock(
        side_effect=[
            document,
            None,
        ]
    )

    ingestion_service = Mock()
    ingestion_service.ingest.return_value = (
        document,
    )

    results = ingest_csv_file(
        csv_path=csv_path,
        mapper=mapper,
        ingestion_service=ingestion_service,
    )

    assert results == (document,)

    ingestion_service.ingest.assert_called_once_with(
        (document,)
    )


def test_ingest_csv_file_returns_empty_tuple_when_all_records_rejected(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "test.csv"

    write_csv(
        csv_path,
        [
            {"id": "", "text": "Invalid"},
        ],
    )

    mapper = Mock(return_value=None)

    ingestion_service = Mock()

    results = ingest_csv_file(
        csv_path=csv_path,
        mapper=mapper,
        ingestion_service=ingestion_service,
    )

    assert results == ()

    ingestion_service.ingest.assert_not_called()


def test_ingest_csv_file_returns_empty_tuple_for_empty_csv(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "empty.csv"

    csv_path.write_text(
        "id,text\n",
        encoding="utf-8",
    )

    mapper = Mock()
    ingestion_service = Mock()

    results = ingest_csv_file(
        csv_path=csv_path,
        mapper=mapper,
        ingestion_service=ingestion_service,
    )

    assert results == ()

    mapper.assert_not_called()
    ingestion_service.ingest.assert_not_called()


def test_ingest_csv_file_does_not_mutate_mapper_documents(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "test.csv"

    write_csv(
        csv_path,
        [
            {"id": "1", "text": "Test"},
        ],
    )

    document = make_document(
        document_id="doc-001",
    )

    original_id = document.id
    original_text = document.text
    original_metadata = dict(document.metadata)

    mapper = Mock(return_value=document)

    ingestion_service = Mock()
    ingestion_service.ingest.return_value = ()

    ingest_csv_file(
        csv_path=csv_path,
        mapper=mapper,
        ingestion_service=ingestion_service,
    )

    assert document.id == original_id
    assert document.text == original_text
    assert document.metadata == original_metadata