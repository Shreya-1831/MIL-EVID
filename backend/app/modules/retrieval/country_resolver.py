"""Resolve configured countries mentioned in a query."""

from __future__ import annotations


def resolve_country(
    query: str,
    countries: tuple[str, ...],
) -> str | None:
    """Return the first configured country explicitly mentioned in the query."""

    if not query or not query.strip():
        return None

    normalized_query = query.casefold()

    for country in countries:
        if country.casefold() in normalized_query:
            return country

    return None