from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import RepositoryError
from app.database.models import EvidenceMetadata
from app.domain.models.evidence import EvidenceDocument


class EvidenceRepository:
    """Persist evidence metadata only.

    Full evidence text and document metadata remain in the local
    JSONL chunk store. PostgreSQL stores only lightweight retrieval
    metadata.
    """

    def __init__(
        self,
        session: Session,
        *,
        batch_size: int = 1000,
    ) -> None:
        self._session = session
        self._batch_size = batch_size

    @staticmethod
    def _document_to_row(
        document: EvidenceDocument,
    ) -> dict:
        return {
            "id": document.id,
            "source": document.source,
            "source_type": document.source_type.value,
            "perspective": (
                document.perspective.value
                if document.perspective is not None
                else None
            ),
            "title": document.title,
            "date": document.date,
            "url": document.url,
            "parent_document_id": document.document_id,
            "chunk_index": document.chunk_index,
        }

    def add_metadata(
        self,
        document: EvidenceDocument,
    ) -> EvidenceMetadata:
        """Persist one document's metadata."""
        self.add_many([document])

        result = self.get_metadata_by_id(document.id)

        if result is None:
            raise RepositoryError(
                f"Evidence metadata was not persisted: {document.id}"
            )

        return result

    def add_many(
        self,
        documents: Sequence[EvidenceDocument],
    ) -> int:
        """Persist metadata for a sequence of documents.

        Existing IDs are ignored.
        Returns the number of input documents processed.
        """
        if not documents:
            return 0

        processed = 0

        for start in range(
            0,
            len(documents),
            self._batch_size,
        ):
            batch = documents[start : start + self._batch_size]

            rows = [
                self._document_to_row(document)
                for document in batch
            ]

            try:
                self._insert_ignore_conflicts(rows)
                self._session.commit()
            except SQLAlchemyError as exc:
                self._session.rollback()
                raise RepositoryError(
                    "Failed to persist evidence metadata batch "
                    f"[{start}:{start + len(batch)}]: {exc}"
                ) from exc

            processed += len(batch)

        return processed

    def _insert_ignore_conflicts(
        self,
        rows: list[dict],
    ) -> None:
        """Insert rows while ignoring duplicate IDs.

        Supports both PostgreSQL and SQLite so repository tests can
        use a lightweight in-memory database.
        """
        dialect = self._session.bind.dialect.name

        if dialect == "postgresql":
            from sqlalchemy.dialects.postgresql import insert

            statement = insert(EvidenceMetadata).values(rows)
            statement = statement.on_conflict_do_nothing(
                index_elements=["id"]
            )

        elif dialect == "sqlite":
            from sqlalchemy.dialects.sqlite import insert

            statement = insert(EvidenceMetadata).values(rows)
            statement = statement.on_conflict_do_nothing(
                index_elements=["id"]
            )

        else:
            statement = EvidenceMetadata.__table__.insert().values(rows)

        self._session.execute(statement)

    def bulk_upsert_evidence_metadata(
        self,
        documents: Sequence[EvidenceDocument],
    ) -> int:
        """Backward-compatible alias for metadata insertion."""
        return self.add_many(documents)

    def get_metadata_by_id(
        self,
        evidence_id: str,
    ) -> EvidenceMetadata | None:
        statement = select(EvidenceMetadata).where(
            EvidenceMetadata.id == evidence_id
        )

        return self._session.execute(
            statement
        ).scalar_one_or_none()

    def get_metadata_by_ids(
        self,
        ids: Sequence[str],
    ) -> list[EvidenceMetadata]:
        if not ids:
            return []

        statement = select(EvidenceMetadata).where(
            EvidenceMetadata.id.in_(ids)
        )

        return list(
            self._session.execute(statement)
            .scalars()
            .all()
        )

    def exists(self, evidence_id: str) -> bool:
        return self.get_metadata_by_id(evidence_id) is not None

    def list_metadata(self) -> list[EvidenceMetadata]:
        statement = select(EvidenceMetadata).order_by(
            EvidenceMetadata.parent_document_id,
            EvidenceMetadata.chunk_index,
        )

        return list(
            self._session.execute(statement)
            .scalars()
            .all()
        )

    def list_metadata_by_document_id(
        self,
        document_id: str,
    ) -> list[EvidenceMetadata]:
        statement = (
            select(EvidenceMetadata)
            .where(
                EvidenceMetadata.parent_document_id == document_id
            )
            .order_by(EvidenceMetadata.chunk_index)
        )

        return list(
            self._session.execute(statement)
            .scalars()
            .all()
        )

    def count(
        self,
        source: str | None = None,
    ) -> int:
        statement = select(EvidenceMetadata)

        if source is not None:
            statement = statement.where(
                EvidenceMetadata.source == source
            )

        return len(
            self._session.execute(statement)
            .scalars()
            .all()
        )