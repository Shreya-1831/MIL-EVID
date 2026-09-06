from __future__ import annotations

from pathlib import Path

from app.database.session import get_session_factory
from app.modules.ingestion.static_ingestion_runner import (
    ingest_sipri_csv,
    ingest_ucdp_dyadic_csv,
    ingest_ucdp_ged_csv,
)


BASE_DIR = Path(__file__).resolve().parent.parent

SIPRI_DIR = BASE_DIR / "data" / "raw" / "sipri"

UCDP_GED_CSV_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "ucdp"
    / "ged_primary_13.csv"
)

UCDP_DYADIC_CSV_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "ucdp"
    / "dyadic_primary_13.csv"
)

SIPRI_FILES = [
    "china_2015_2025.csv",
    "france_2015_2025.csv",
    "germany_2015_2025.csv",
    "india_2015_2025.csv",
    "israel_2015_2025.csv",
    "pakistan_2015_2025.csv",
    "russia_2015_2025.csv",
    "ukraine_2015_2025.csv",
    "uk_2015_2025.csv",
    "us_2015_2025.csv",
]


def main() -> None:
    """Ingest all configured static datasets."""

    session_factory = get_session_factory()

    with session_factory() as session:
        print("Starting static data ingestion...\n")

        # ---------------------------------------------------------
        # SIPRI
        # ---------------------------------------------------------
        total_sipri = 0

        for filename in SIPRI_FILES:
            csv_path = SIPRI_DIR / filename

            print(f"Ingesting SIPRI: {filename}")

            count = ingest_sipri_csv(
                csv_path=csv_path,
                session=session,
            )

            total_sipri += count

            print(
                f"SIPRI {filename} completed: "
                f"{count} documents persisted.\n"
            )

        # ---------------------------------------------------------
        # UCDP GED - filtered 13-country dataset
        # ---------------------------------------------------------
        print("Ingesting UCDP GED (filtered 13-country dataset)...")

        ucdp_ged_count = ingest_ucdp_ged_csv(
            csv_path=UCDP_GED_CSV_PATH,
            session=session,
        )

        print(
            f"UCDP GED ingestion completed: "
            f"{ucdp_ged_count} documents persisted.\n"
        )

        # ---------------------------------------------------------
        # UCDP Dyadic - filtered 13-country dataset
        # ---------------------------------------------------------
        print("Ingesting UCDP Dyadic (filtered 13-country dataset)...")

        ucdp_dyadic_count = ingest_ucdp_dyadic_csv(
            csv_path=UCDP_DYADIC_CSV_PATH,
            session=session,
        )

        print(
            f"UCDP Dyadic ingestion completed: "
            f"{ucdp_dyadic_count} documents persisted.\n"
        )

        # Commit all metadata changes.
        session.commit()

        total = (
            total_sipri
            + ucdp_ged_count
            + ucdp_dyadic_count
        )

        print("=" * 60)
        print("STATIC DATA INGESTION COMPLETED")
        print("=" * 60)
        print(f"SIPRI documents processed:        {total_sipri}")
        print(f"UCDP GED documents processed:     {ucdp_ged_count}")
        print(f"UCDP Dyadic documents processed:  {ucdp_dyadic_count}")
        print(f"Total documents processed:        {total}")


if __name__ == "__main__":
    main()