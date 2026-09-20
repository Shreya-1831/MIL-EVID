from unittest.mock import Mock

from app.domain.enums import Perspective, SourceType
from app.domain.models.evidence import EvidenceDocument
from app.modules.ingestion.acled_client import ACLEDClient
from app.modules.retrieval.acled_retriever import (
    ACLEDDynamicRetriever,
    MILITARY_EVENT_TYPES,
)


def _make_event(
    event_id: str = "IND12345",
    event_type: str = "Battles",
) -> dict:
    return {
        "event_id_cnty": event_id,
        "event_date": "2026-09-01",
        "event_type": event_type,
        "sub_event_type": "Armed clash",
        "actor1": "Military Forces",
        "actor2": "Armed Group",
        "country": "India",
        "location": "Test Location",
        "fatalities": "2",
        "notes": "Test ACLED event.",
        "timestamp": "2026-09-10 12:00:00+00:00",
    }


def _make_document(event_id: str) -> EvidenceDocument:
    return EvidenceDocument(
        id=f"acled-{event_id}",
        document_id=f"acled-{event_id}",
        chunk_index=0,
        text="Test ACLED military event.",
        source="ACLED",
        source_type=SourceType.ACLED,
        perspective=Perspective.MILITARY,
        title="Battles — Test Location",
    )


def test_retrieve_returns_military_relevant_events(monkeypatch):
    client = Mock(spec=ACLEDClient)
    client.get_events.return_value = (
        _make_event("IND001", "Battles"),
        _make_event("IND002", "Protests"),
        _make_event("IND003", "Violence against civilians"),
    )

    monkeypatch.setattr(
        "app.modules.retrieval.acled_retriever.map_acled_event",
        lambda event: _make_document(event["event_id_cnty"]),
    )

    retriever = ACLEDDynamicRetriever(client)

    documents = retriever.retrieve(
        country="India",
        updated_since="2026-09-01",
        limit=20,
    )

    assert len(documents) == 2
    assert [document.id for document in documents] == [
        "acled-IND001",
        "acled-IND003",
    ]


def test_retrieve_passes_filters_to_acled_client(monkeypatch):
    client = Mock(spec=ACLEDClient)
    client.get_events.return_value = ()

    retriever = ACLEDDynamicRetriever(client)

    retriever.retrieve(
        country="Ukraine",
        updated_since="2026-09-01",
        limit=25,
    )

    # client.get_events.assert_called_once_with(
    #     country="Ukraine",
    #     updated_since="2026-09-01",
    #     limit=25,
    # )
    assert client.get_events.call_count == 4

    for call in client.get_events.call_args_list:
        assert call.kwargs["country"] == "Ukraine"
        assert call.kwargs["updated_since"] == "2026-09-01"
        assert call.kwargs["limit"] == 25
        assert call.kwargs["start_date"] is None
        assert call.kwargs["end_date"] is None

    assert {
        call.kwargs["event_type"]
        for call in client.get_events.call_args_list
    } == {
        "Explosions/Remote violence",
        "Strategic developments",
        "Battles",
        "Violence against civilians",
    }


def test_retrieve_can_include_all_event_types(monkeypatch):
    client = Mock(spec=ACLEDClient)
    client.get_events.return_value = (
        _make_event("IND001", "Battles"),
        _make_event("IND002", "Protests"),
        _make_event("IND003", "Riots"),
    )

    monkeypatch.setattr(
        "app.modules.retrieval.acled_retriever.map_acled_event",
        lambda event: _make_document(event["event_id_cnty"]),
    )

    retriever = ACLEDDynamicRetriever(client)

    documents = retriever.retrieve(
        country="India",
        include_all_event_types=True,
    )

    assert len(documents) == 3


def test_retrieve_skips_unmappable_events(monkeypatch):
    client = Mock(spec=ACLEDClient)
    client.get_events.return_value = (
        _make_event("IND001", "Battles"),
        _make_event("IND002", "Battles"),
    )

    def fake_mapper(event):
        if event["event_id_cnty"] == "IND002":
            return None
        return _make_document(event["event_id_cnty"])

    monkeypatch.setattr(
        "app.modules.retrieval.acled_retriever.map_acled_event",
        fake_mapper,
    )

    retriever = ACLEDDynamicRetriever(client)

    documents = retriever.retrieve(country="India")

    assert len(documents) == 1
    assert documents[0].id == "acled-IND001"


def test_military_event_types_are_defined():
    assert "Battles" in MILITARY_EVENT_TYPES
    assert "Explosions/Remote violence" in MILITARY_EVENT_TYPES
    assert "Violence against civilians" in MILITARY_EVENT_TYPES
    assert "Strategic developments" in MILITARY_EVENT_TYPES