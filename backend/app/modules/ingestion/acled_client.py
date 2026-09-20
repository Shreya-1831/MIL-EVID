"""Client for retrieving dynamic ACLED conflict-event data."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from acled import AcledClient
from datetime import datetime, timezone

class ACLEDClient:
    """Thin wrapper around the ACLED Python client."""

    def __init__(
        self,
        *,
        username: str,
        password: str,
    ) -> None:
        if not username.strip():
            raise ValueError("ACLED username must not be blank.")

        if not password:
            raise ValueError("ACLED password must not be blank.")

        self._client = AcledClient(
            username=username,
            password=password,
        )

    def _to_unix_timestamp(self, value: str) -> int:
        """Convert an ISO date/datetime string to a Unix timestamp."""
        normalized = value.strip()

        if len(normalized) == 10:
            parsed = datetime.fromisoformat(normalized).replace(
                tzinfo=timezone.utc
            )
        else:
            parsed = datetime.fromisoformat(
                normalized.replace("Z", "+00:00")
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)

        return int(parsed.timestamp())

    def get_events(
        self,
        *,
        country: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        updated_since: str | None = None,
        event_type: str | None = None,
        limit: int = 50,
    ) -> tuple[Mapping[str, Any], ...]:
        """Fetch ACLED events matching the requested filters."""
        if limit <= 0:
            raise ValueError("limit must be greater than zero.")

        params: dict[str, Any] = {"limit": limit}

        if country:
            params["country"] = country

        if event_type:
            params["event_type"] = event_type
        
        if start_date and end_date:
            params["event_date"] = f"{start_date}|{end_date}"
            query_params = {"event_date_where": "BETWEEN"}
        else:
            query_params = {}

        if updated_since:
            timestamp = self._to_unix_timestamp(updated_since)
            query_params["timestamp_where"] = ">="
            params["timestamp"] = timestamp

        events = self._client.get_data(
            **params,
            query_params=query_params,
        )

        return tuple(events)

