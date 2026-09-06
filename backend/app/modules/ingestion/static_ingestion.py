"""Static CSV ingestion utilities."""

from __future__ import annotations

import csv
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol, TextIO

from app.domain.models.evidence import EvidenceDocument


DEFAULT_BATCH_SIZE = 500


class EvidenceIngestionServiceProtocol(Protocol):
    """Protocol for the evidence ingestion service."""

    def ingest(
        self,
        documents: Sequence[EvidenceDocument],
    ) -> tuple[EvidenceDocument, ...]:
        """Ingest evidence documents."""


RecordMapper = Callable[
    [dict[str, str]],
    EvidenceDocument | None,
]


def _detect_csv_encoding(
    csv_path: Path,
) -> str:
    """Detect a supported encoding by validating the complete file."""

    encodings = (
        "utf-8-sig",
        "utf-8",
        "cp1252",
        "latin-1",
    )

    last_error: UnicodeDecodeError | None = None

    for encoding in encodings:
        try:
            with csv_path.open(
                mode="r",
                encoding=encoding,
                newline="",
            ) as csv_file:
                while csv_file.read(1024 * 1024):
                    pass

            return encoding

        except UnicodeDecodeError as error:
            last_error = error

    if last_error is not None:
        raise last_error

    raise ValueError(
        f"Unable to detect CSV encoding: {csv_path}"
    )


def _open_csv(
    csv_path: Path,
) -> TextIO:
    """Open a CSV file using a detected supported encoding."""

    encoding = _detect_csv_encoding(csv_path)

    return csv_path.open(
        mode="r",
        encoding=encoding,
        newline="",
    )


def ingest_csv_file(
    *,
    csv_path: Path,
    mapper: RecordMapper,
    ingestion_service: EvidenceIngestionServiceProtocol,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> tuple[EvidenceDocument, ...]:
    """Read, preprocess, and ingest a CSV file in batches.

    Processing in batches prevents large datasets from being loaded and
    preprocessed as one large in-memory collection.
    """

    if batch_size <= 0:
        raise ValueError(
            "batch_size must be greater than zero."
        )

    persisted_documents: list[EvidenceDocument] = []
    batch: list[EvidenceDocument] = []

    processed_records = 0
    valid_documents = 0
    persisted_count = 0

    with _open_csv(csv_path) as csv_file:
        reader = csv.DictReader(csv_file)

        for record in reader:
            processed_records += 1

            document = mapper(dict(record))

            if document is None:
                continue

            batch.append(document)
            valid_documents += 1

            if len(batch) < batch_size:
                continue

            persisted_batch = ingestion_service.ingest(
                tuple(batch)
            )

            persisted_documents.extend(
                persisted_batch
            )

            persisted_count += len(
                persisted_batch
            )

            print(
                f"Processed {processed_records:,} records | "
                f"Persisted {persisted_count:,} documents"
            )

            batch = []

    if batch:
        persisted_batch = ingestion_service.ingest(
            tuple(batch)
        )

        persisted_documents.extend(
            persisted_batch
        )

        persisted_count += len(
            persisted_batch
        )

        print(
            f"Processed {processed_records:,} records | "
            f"Persisted {persisted_count:,} documents"
        )

    print(
        "CSV ingestion completed | "
        f"Total records: {processed_records:,} | "
        f"Valid documents: {valid_documents:,} | "
        f"Persisted: {persisted_count:,}"
    )

    return tuple(persisted_documents)