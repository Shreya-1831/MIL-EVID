"""Dynamic ACLED retrieval for current military/conflict evidence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.domain.models.evidence import EvidenceDocument
from app.modules.ingestion.acled_client import ACLEDClient
from app.modules.ingestion.acled_mapper import map_acled_event


MILITARY_EVENT_TYPES = {
    "Battles",
    "Explosions/Remote violence",
    "Violence against civilians",
    "Strategic developments",
}


class ACLEDDynamicRetriever:
    """Retrieve recent ACLED events and convert them to evidence documents."""

    def __init__(self, client: ACLEDClient) -> None:
        self._client = client

    def retrieve(
        self,
        *,
        country: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        updated_since: str | None = None,
        limit: int = 20,
        include_all_event_types: bool = False,
    ) -> tuple[EvidenceDocument, ...]:
        """Fetch and map ACLED events relevant to military analysis."""

        if include_all_event_types:
            events = self._client.get_events(
                country=country,
                start_date=start_date,
                end_date=end_date,
                updated_since=updated_since,
                limit=limit,
            )
        else:
            events = []

            for event_type in MILITARY_EVENT_TYPES:
                type_events = self._client.get_events(
                    country=country,
                    event_type=event_type,
                    start_date=start_date,
                    end_date=end_date,
                    updated_since=updated_since,
                    limit=limit,
                )
                events.extend(type_events)

        events = sorted(
            events,
            key=lambda event: str(event.get("timestamp") or ""),
            reverse=True,
        )

        if not events and start_date and end_date:
            from datetime import date, timedelta

            fallback_start = (
                date.fromisoformat(end_date) - timedelta(days=60)
            ).isoformat()

            print(
                f"ACLED: no events from {start_date} to {end_date}, "
                f"expanding to {fallback_start} to {end_date}..."
            )

            events = self._client.get_events(
                country=country,
                start_date=fallback_start,
                end_date=end_date,
                limit=limit,
            )

        events = sorted(
            events,
            key=lambda event: str(event.get("timestamp") or ""),
            reverse=True,
        )

        documents: list[EvidenceDocument] = []

        seen_ids: set[str] = set()

        for event in events:
            event_id = str(
                event.get("event_id_cnty")
                or event.get("data_id")
                or ""
            )

            if event_id and event_id in seen_ids:
                continue

            if (
                not include_all_event_types
                and not self._is_military_relevant(event)
            ):
                continue

            document = map_acled_event(event)

            if document is not None:
                documents.append(document)

                if event_id:
                    seen_ids.add(event_id)

        return tuple(documents)

    @staticmethod
    def _is_military_relevant(
        event: Mapping[str, Any],
    ) -> bool:
        """Return whether an ACLED event is relevant to military analysis."""

        event_type = event.get("event_type")

        if event_type is None:
            return False

        return str(event_type).strip() in MILITARY_EVENT_TYPES