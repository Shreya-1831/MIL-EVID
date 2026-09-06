from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import Base
from app.domain.enums import Perspective, SourceType
from app.domain.models.evidence import EvidenceDocument
from app.repositories.evidence_repository import EvidenceRepository


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite+pysqlite:///:memory:")

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


@pytest.fixture
def repository(session: Session) -> EvidenceRepository:
    return EvidenceRepository(session)


def make_document(
    *,
    id: str = "doc-001::chunk-0000",
    document_id: str = "doc-001",
    chunk_index: int = 0,
    source: str = "Test Source",
    source_type: SourceType = SourceType.UCDP,
    perspective: Perspective | None = Perspective.HISTORICAL,
) -> EvidenceDocument:
    return EvidenceDocument(
        id=id,
        document_id=document_id,
        chunk_index=chunk_index,
        text="Full evidence text stored outside PostgreSQL.",
        source=source,
        source_type=source_type,
        perspective=perspective,
        title="Test Evidence",
        date=None,
        url="https://example.com",
        metadata={
            "test": True,
            "parent_document_id": document_id,
        },
    )


def test_add_metadata(repository: EvidenceRepository) -> None:
    document = make_document()

    saved = repository.add_metadata(document)

    assert saved.id == document.id
    assert saved.source == document.source
    assert saved.source_type == document.source_type.value
    assert saved.perspective == document.perspective.value
    assert saved.title == document.title
    assert saved.url == document.url
    assert saved.parent_document_id == document.document_id
    assert saved.chunk_index == document.chunk_index


def test_get_metadata_by_id(
    repository: EvidenceRepository,
) -> None:
    document = make_document()

    repository.add_metadata(document)

    result = repository.get_metadata_by_id(document.id)

    assert result is not None
    assert result.id == document.id
    assert result.parent_document_id == "doc-001"
    assert result.chunk_index == 0


def test_get_metadata_by_id_returns_none_when_missing(
    repository: EvidenceRepository,
) -> None:
    assert repository.get_metadata_by_id("missing-id") is None


def test_exists(repository: EvidenceRepository) -> None:
    document = make_document()

    assert repository.exists(document.id) is False

    repository.add_metadata(document)

    assert repository.exists(document.id) is True


def test_add_many(repository: EvidenceRepository) -> None:
    documents = [
        make_document(
            id="doc-001::chunk-0000",
            chunk_index=0,
        ),
        make_document(
            id="doc-001::chunk-0001",
            chunk_index=1,
        ),
    ]

    saved = repository.add_many(documents)

    assert saved == 2
    assert repository.count() == 2


def test_add_many_empty_input(
    repository: EvidenceRepository,
) -> None:
    assert repository.add_many([]) == 0


def test_duplicate_ids_are_ignored(
    repository: EvidenceRepository,
) -> None:
    document = make_document()

    assert repository.add_many([document, document]) == 2
    assert repository.count() == 1


def test_list_metadata_orders_by_document_and_chunk(
    repository: EvidenceRepository,
) -> None:
    documents = [
        make_document(
            id="doc-002::chunk-0001",
            document_id="doc-002",
            chunk_index=1,
        ),
        make_document(
            id="doc-001::chunk-0001",
            document_id="doc-001",
            chunk_index=1,
        ),
        make_document(
            id="doc-001::chunk-0000",
            document_id="doc-001",
            chunk_index=0,
        ),
        make_document(
            id="doc-002::chunk-0000",
            document_id="doc-002",
            chunk_index=0,
        ),
    ]

    repository.add_many(documents)

    results = repository.list_metadata()

    assert [
        (row.parent_document_id, row.chunk_index)
        for row in results
    ] == [
        ("doc-001", 0),
        ("doc-001", 1),
        ("doc-002", 0),
        ("doc-002", 1),
    ]


def test_list_metadata_by_document_id(
    repository: EvidenceRepository,
) -> None:
    documents = [
        make_document(
            id="doc-001::chunk-0002",
            document_id="doc-001",
            chunk_index=2,
        ),
        make_document(
            id="doc-001::chunk-0000",
            document_id="doc-001",
            chunk_index=0,
        ),
        make_document(
            id="doc-001::chunk-0001",
            document_id="doc-001",
            chunk_index=1,
        ),
        make_document(
            id="doc-002::chunk-0000",
            document_id="doc-002",
            chunk_index=0,
        ),
    ]

    repository.add_many(documents)

    results = repository.list_metadata_by_document_id("doc-001")

    assert [
        row.chunk_index
        for row in results
    ] == [0, 1, 2]

    assert all(
        row.parent_document_id == "doc-001"
        for row in results
    )


def test_count_by_source(
    repository: EvidenceRepository,
) -> None:
    repository.add_many(
        [
            make_document(
                id="ucdp-001",
                source="UCDP",
            ),
            make_document(
                id="ucdp-002",
                source="UCDP",
            ),
            make_document(
                id="sipri-001",
                source="SIPRI",
                source_type=SourceType.SIPRI,
            ),
        ]
    )

    assert repository.count() == 3
    assert repository.count(source="UCDP") == 2
    assert repository.count(source="SIPRI") == 1


def test_optional_perspective_is_preserved(
    repository: EvidenceRepository,
) -> None:
    document = make_document(perspective=None)

    saved = repository.add_metadata(document)

    assert saved.perspective is None