from __future__ import annotations

import csv
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import Base
from app.modules.ingestion.static_ingestion_runner import (
    ingest_sipri_csv,
    ingest_ucdp_dyadic_csv,
    ingest_ucdp_ged_csv,
)


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
    )

    Base.metadata.create_all(bind=engine)

    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    database_session = session_factory()

    try:
        yield database_session
    finally:
        database_session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def write_csv(
    path: Path,
    rows: list[dict[str, str]],
) -> None:
    if not rows:
        path.write_text(
            "",
            encoding="utf-8",
        )
        return

    with path.open(
        mode="w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=list(rows[0].keys()),
        )

        writer.writeheader()
        writer.writerows(rows)


def test_ingest_sipri_csv_end_to_end(
    tmp_path: Path,
    session: Session,
) -> None:
    csv_path = tmp_path / "sipri.csv"

    write_csv(
        csv_path,
        [
            {
                "Recipient": "India",
                "Supplier": "Russia",
                "Year of order": "2019",
                "Weapon designation": "RBU-6000",
                "Weapon description": (
                    "anti-submarine rocket launcher"
                ),
                "Number ordered": "16",
                "status": "New",
                "Comments": "Test record",
            },
        ],
    )

    count = ingest_sipri_csv(
        csv_path=csv_path,
        session=session,
    )

    assert count > 0


def test_ingest_ucdp_ged_csv_end_to_end(
    tmp_path: Path,
    session: Session,
) -> None:
    csv_path = tmp_path / "ged.csv"

    write_csv(
        csv_path,
        [
            {
                "id": "1568",
                "relid": "ALG-1992-1-1-6",
                "year": "1992",
                "conflict_name": "Algeria: Government",
                "side_a": "Government of Algeria",
                "side_b": "AIS",
                "country": "Algeria",
                "region": "Africa",
                "date_start": "1992-03-17 00:00:00.000",
                "date_end": "1992-03-17 00:00:00.000",
                "best": "2",
                "source_article": "Test source article.",
                "where_description": "Medea town",
            },
        ],
    )

    count = ingest_ucdp_ged_csv(
        csv_path=csv_path,
        session=session,
    )

    assert count > 0


def test_ingest_ucdp_dyadic_csv_end_to_end(
    tmp_path: Path,
    session: Session,
) -> None:
    csv_path = tmp_path / "dyadic.csv"

    write_csv(
        csv_path,
        [
            {
                "dyad_id": "399",
                "conflict_id": "200",
                "location": "Bolivia",
                "side_a": "Government of Bolivia",
                "side_b": (
                    "Popular Revolutionary Movement"
                ),
                "incompatibility": "2",
                "year": "1946",
                "intensity_level": "2",
                "type_of_conflict": "3",
                "start_date": "1946-07-18",
                "region": "5",
                "version": "26.1",
            },
        ],
    )

    count = ingest_ucdp_dyadic_csv(
        csv_path=csv_path,
        session=session,
    )

    assert count > 0