"""Create filtered UCDP MVP datasets."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Callable, Iterator, Iterable

from app.core.config import get_settings
from app.modules.preprocessing.country_filter import (
    build_primary_country_set,
    filter_ucdp_dyadic_records,
    filter_ucdp_ged_records,
)


RAW_UCDP_DIR = Path("data/raw/ucdp")
PROCESSED_UCDP_DIR = Path("data/processed/ucdp")

GED_INPUT = RAW_UCDP_DIR / "ged_csv.csv"
DYADIC_INPUT = RAW_UCDP_DIR / "dyadic_csv.csv"

GED_OUTPUT = PROCESSED_UCDP_DIR / "ged_primary_13.csv"
DYADIC_OUTPUT = PROCESSED_UCDP_DIR / "dyadic_primary_13.csv"


RecordFilter = Callable[
    [Iterable[dict[str, Any]], frozenset[str]],
    Iterator[dict[str, Any]],
]


def filter_csv(
    input_path: Path,
    output_path: Path,
    *,
    record_filter: RecordFilter,
    primary_country_set: frozenset[str],
) -> tuple[int, int]:
    """Filter a CSV using streaming I/O."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    total_rows = 0
    kept_rows = 0

    with (
        input_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as source,
        output_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as target,
    ):
        reader = csv.DictReader(source)

        if not reader.fieldnames:
            raise ValueError(
                f"CSV has no header: {input_path}"
            )

        writer = csv.DictWriter(
            target,
            fieldnames=reader.fieldnames,
        )
        writer.writeheader()

        for record in reader:
            total_rows += 1

            if record_filter(
                (record,),
                primary_country_set,
            ):
                writer.writerow(record)
                kept_rows += 1

    return total_rows, kept_rows


def stream_filter_csv(
    input_path: Path,
    output_path: Path,
    *,
    record_filter: RecordFilter,
    primary_country_set: frozenset[str],
) -> tuple[int, int]:
    """Filter a CSV while preserving streaming behavior."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    total_rows = 0
    kept_rows = 0

    with (
        input_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as source,
        output_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as target,
    ):
        reader = csv.DictReader(source)

        if not reader.fieldnames:
            raise ValueError(
                f"CSV has no header: {input_path}"
            )

        writer = csv.DictWriter(
            target,
            fieldnames=reader.fieldnames,
        )
        writer.writeheader()

        filtered_records = record_filter(
            reader,
            primary_country_set,
        )

        for record in filtered_records:
            writer.writerow(record)
            kept_rows += 1

        total_rows = reader.line_num - 1

    return total_rows, kept_rows


def main() -> None:
    settings = get_settings()

    primary_country_set = build_primary_country_set(
        settings.primary_countries
    )

    if not primary_country_set:
        raise ValueError(
            "PRIMARY_COUNTRIES is empty."
        )

    print("Primary countries:")
    for country in settings.primary_countries:
        print(f"  - {country}")

    print("\nFiltering UCDP GED...")

    ged_total, ged_kept = stream_filter_csv(
        GED_INPUT,
        GED_OUTPUT,
        record_filter=filter_ucdp_ged_records,
        primary_country_set=primary_country_set,
    )

    print(f"  Input : {ged_total:,} rows")
    print(f"  Output: {ged_kept:,} rows")
    print(f"  File  : {GED_OUTPUT}")

    print("\nFiltering UCDP Dyadic...")

    dyadic_total, dyadic_kept = stream_filter_csv(
        DYADIC_INPUT,
        DYADIC_OUTPUT,
        record_filter=filter_ucdp_dyadic_records,
        primary_country_set=primary_country_set,
    )

    print(f"  Input : {dyadic_total:,} rows")
    print(f"  Output: {dyadic_kept:,} rows")
    print(f"  File  : {DYADIC_OUTPUT}")

    print("\n✓ UCDP filtering complete.")


if __name__ == "__main__":
    main()