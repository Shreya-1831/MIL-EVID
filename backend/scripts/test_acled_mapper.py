"""Test live ACLED retrieval and mapping."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from app.modules.ingestion.acled_client import ACLEDClient
from app.modules.ingestion.acled_mapper import map_acled_event


def main() -> None:
    load_dotenv()

    username = os.getenv("ACLED_USERNAME")
    password = os.getenv("ACLED_PASSWORD")

    if not username or not password:
        raise RuntimeError(
            "ACLED_USERNAME and ACLED_PASSWORD must be set."
        )

    client = ACLEDClient(
        username=username,
        password=password,
    )

    print("=" * 80)
    print("MIL-EVID — ACLED LIVE RETRIEVAL + MAPPING TEST")
    print("=" * 80)

    print("\n[1] Fetching ACLED events...")

    # events = client.get_events(
    #     country="Ukraine",
    #     limit=5,
    # )
    # events = client.get_events(
    #     # country="Ukraine",
    #     country="India",
    #     start_date="2026-01-01",
    #     # end_date="2026-09-13",
    #     limit=10,
    # )
    # events = client.get_events(
    #     country="India",
    #     updated_since="2021-01-01",
    #     limit=10,
    # )
    events = client.get_events(
        country="India",
        updated_since="2026-01-01",
        limit=10,
    )

    print(f"Retrieved {len(events)} raw events.")

    print("\n[2] Mapping events to EvidenceDocument...")

    documents = tuple(
        document
        for event in events
        if (document := map_acled_event(event)) is not None
    )

    print(f"Mapped {len(documents)} events.")

    print("\n[3] Inspecting mapped evidence...\n")

    for index, document in enumerate(documents, start=1):
        print(f"--- Event {index} ---")
        print(f"ID:          {document.id}")
        print(f"Source:      {document.source}")
        print(f"Source type: {document.source_type}")
        print(f"Perspective: {document.perspective}")
        print(f"Title:       {document.title}")
        print(f"Date:        {document.date}")
        print(f"Text:        {document.text[:500]}")

        print("Metadata:")
        print(f"  event_id:  {document.metadata.get('event_id_cnty')}")
        print(f"  type:      {document.metadata.get('event_type')}")
        print(f"  subtype:   {document.metadata.get('sub_event_type')}")
        print(f"  country:   {document.metadata.get('country')}")
        print(f"  location:  {document.metadata.get('location')}")
        print(f"  fatalities:{document.metadata.get('fatalities')}")
        print(f"  timestamp: {document.metadata.get('timestamp')}")
        print()

    print("=" * 80)
    print("ACLED MAPPING TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()