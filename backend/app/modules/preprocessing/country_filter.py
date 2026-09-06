"""Country filtering utilities for MIL-EVID."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import Any

from app.domain.models.evidence import EvidenceDocument


# Canonical aliases used by UCDP and other datasets.
_COUNTRY_ALIASES: dict[str, str] = {
    # United States
    "us": "united states",
    "u.s.": "united states",
    "u.s.a.": "united states",
    "usa": "united states",
    "united states of america": "united states",

    # United Kingdom
    "uk": "united kingdom",
    "u.k.": "united kingdom",
    "great britain": "united kingdom",
    "britain": "united kingdom",

    # China
    "prc": "china",
    "people's republic of china": "china",

    # Russia
    "russian federation": "russia",
    "russia (soviet union)": "russia",
    "soviet union": "russia",
    "ussr": "russia",

    # Colombia
    "columbia": "colombia",

    # Palestine
    "state of palestine": "palestine",
    "palestinian territories": "palestine",
    "occupied palestinian territory": "palestine",
    "occupied palestinian territories": "palestine",
}


def normalize_country_name(raw: str) -> str:
    """Normalize a country name to its canonical form."""
    cleaned = raw.strip().lower()
    return _COUNTRY_ALIASES.get(cleaned, cleaned)


def build_primary_country_set(
    primary_countries: Iterable[str],
) -> frozenset[str]:
    """Build a normalized set of primary countries."""
    return frozenset(
        normalize_country_name(country)
        for country in primary_countries
    )


def is_primary_country(
    country: str | None,
    primary_country_set: frozenset[str],
) -> bool:
    """Check whether a country belongs to the primary-country set."""
    if not primary_country_set:
        return True

    if not country:
        return False

    return normalize_country_name(country) in primary_country_set


def _split_location_countries(value: str | None) -> Iterator[str]:
    """Yield individual countries from a UCDP location field."""
    if not value:
        return

    for part in value.split(","):
        country = part.strip()
        if country:
            yield country


def location_contains_primary_country(
    location: str | None,
    primary_country_set: frozenset[str],
) -> bool:
    """Check whether a UCDP location contains a primary country."""
    if not primary_country_set:
        return True

    return any(
        is_primary_country(country, primary_country_set)
        for country in _split_location_countries(location)
    )


def is_ucdp_ged_record_in_scope(
    record: dict[str, Any],
    primary_country_set: frozenset[str],
) -> bool:
    """Filter UCDP GED using the actual event country.

    GED uses the `country` field as the geographic event location.
    Conflict/actor fields are intentionally not used for filtering.
    """
    return is_primary_country(
        record.get("country"),
        primary_country_set,
    )


def is_ucdp_dyadic_record_in_scope(
    record: dict[str, Any],
    primary_country_set: frozenset[str],
) -> bool:
    """Filter UCDP Dyadic by geographic location.

    A row is retained when:
    1. Any country in `location` is a primary country, or
    2. `territory_name` explicitly identifies Palestine.
    """
    if not primary_country_set:
        return True

    if location_contains_primary_country(
        record.get("location"),
        primary_country_set,
    ):
        return True

    territory = record.get("territory_name")

    if (
        "palestine" in primary_country_set
        and territory
        and normalize_country_name(territory) == "palestine"
    ):
        return True

    return False


def filter_ucdp_ged_records(
    records: Iterable[dict[str, Any]],
    primary_country_set: frozenset[str],
) -> Iterator[dict[str, Any]]:
    """Stream-filter UCDP GED records."""
    for record in records:
        if is_ucdp_ged_record_in_scope(
            record,
            primary_country_set,
        ):
            yield record


def filter_ucdp_dyadic_records(
    records: Iterable[dict[str, Any]],
    primary_country_set: frozenset[str],
) -> Iterator[dict[str, Any]]:
    """Stream-filter UCDP Dyadic records."""
    for record in records:
        if is_ucdp_dyadic_record_in_scope(
            record,
            primary_country_set,
        ):
            yield record


def filter_raw_records(
    records: Iterable[dict[str, Any]],
    *,
    country_key: str,
    primary_country_set: frozenset[str],
) -> Iterator[dict[str, Any]]:
    """Generic raw-record filter for datasets with one country field."""
    for record in records:
        if is_primary_country(
            record.get(country_key),
            primary_country_set,
        ):
            yield record


def filter_documents(
    documents: Iterable[EvidenceDocument],
    *,
    primary_country_set: frozenset[str],
    country_extractor: Callable[
        [EvidenceDocument],
        str | None,
    ] = lambda doc: doc.metadata.get("country"),
) -> tuple[EvidenceDocument, ...]:
    """Filter already-mapped evidence documents by country."""
    return tuple(
        document
        for document in documents
        if is_primary_country(
            country_extractor(document),
            primary_country_set,
        )
    )