"""Repository for MIL-EVID analysis persistence."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import RepositoryError
from app.database.models import (
    Analysis,
    AnalysisContradiction,
    AnalysisEvidence as AnalysisEvidenceRow,
    AnalysisPerspective,
    Claim,
    ClaimEvidence,
    Query,
)
from app.domain.models.analysis import (
    AnalysisEvidence,
    FinalAnalysisResponse,
)


class AnalysisRepository:
    """Persist and retrieve complete MIL-EVID analysis results."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_analysis(
        self,
        *,
        user_id: UUID,
        query_text: str,
        result: FinalAnalysisResponse,
        evidence: Sequence[AnalysisEvidence],
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> Analysis:
        """Persist one complete analysis in a single transaction."""

        try:
            query_record = Query(
                user_id=user_id,
                query_text=query_text,
            )
            self._session.add(query_record)
            self._session.flush()

            analysis_record = Analysis(
                query_id=query_record.id,
                status="completed",
                final_answer=self._build_final_answer(result),
                overall_confidence=float(
                    result.confidence.final_score
                ),
                started_at=started_at,
                completed_at=completed_at,
            )
            self._session.add(analysis_record)
            self._session.flush()

            self._add_perspectives(
                analysis_id=analysis_record.id,
                result=result,
            )

            evidence_map = self._add_evidence(
                analysis_id=analysis_record.id,
                evidence=evidence,
            )

            self._add_claims(
                analysis_id=analysis_record.id,
                result=result,
                evidence_map=evidence_map,
            )

            self._add_contradictions(
                analysis_id=analysis_record.id,
                result=result,
            )

            self._session.commit()
            self._session.refresh(analysis_record)

            return analysis_record

        except SQLAlchemyError as exc:
            self._session.rollback()
            raise RepositoryError(
                f"Failed to persist analysis: {exc}"
            ) from exc

    def _add_perspectives(
        self,
        *,
        analysis_id: UUID,
        result: FinalAnalysisResponse,
    ) -> None:
        perspectives = (
            result.military_analysis,
            result.legal_analysis,
            result.historical_analysis,
        )

        rows = [
            AnalysisPerspective(
                analysis_id=analysis_id,
                perspective=perspective.perspective.value,
                analysis_text=perspective.analysis_text,
            )
            for perspective in perspectives
        ]

        self._session.add_all(rows)

    def _add_evidence(
        self,
        *,
        analysis_id: UUID,
        evidence: Sequence[AnalysisEvidence],
    ) -> dict[str, UUID]:
        """Persist evidence snapshots used by the analysis."""

        evidence_map: dict[str, UUID] = {}

        for document in evidence:
            if document.evidence_id in evidence_map:
                continue

            row = AnalysisEvidenceRow(
                analysis_id=analysis_id,
                evidence_id=document.evidence_id,
                source_name=document.source,
                source_type=document.source_type.value,
                title=document.title,
                evidence_text=document.text,
                source_url=document.url,
                publication_date=document.date,
                perspective=(
                    document.perspective.value
                    if document.perspective is not None
                    else None
                ),
                relevance_score=None,
                document_id=document.document_id,
                chunk_index=document.chunk_index,
                reranker_score=document.reranker_score,
                original_rrf_score=document.original_rrf_score,
            )

            self._session.add(row)
            self._session.flush()

            evidence_map[document.evidence_id] = row.id

        return evidence_map

    def _add_claims(
        self,
        *,
        analysis_id: UUID,
        result: FinalAnalysisResponse,
        evidence_map: dict[str, UUID],
    ) -> None:
        perspective_by_claim = self._build_claim_perspectives(result)

        for verification in result.claim_verification:
            claim_text = verification.claim.strip()

            if not claim_text:
                continue

            claim_record = Claim(
                analysis_id=analysis_id,
                claim_text=claim_text,
                perspective=perspective_by_claim.get(
                    self._normalize_claim(claim_text)
                ),
                verdict=verification.status.value,
                support_score=float(verification.support_score),
                verified=verification.verified,
            )

            self._session.add(claim_record)
            self._session.flush()

            relationships: list[ClaimEvidence] = []

            for evidence_id in verification.supporting_evidence_ids:
                postgres_evidence_id = evidence_map.get(
                    str(evidence_id)
                )

                if postgres_evidence_id is None:
                    continue

                relationships.append(
                    ClaimEvidence(
                        claim_id=claim_record.id,
                        evidence_id=postgres_evidence_id,
                        support_type=self._support_type(
                            verification.status.value
                        ),
                        confidence=float(
                            verification.support_score
                        ),
                    )
                )

            if relationships:
                self._session.add_all(relationships)

    def _add_contradictions(
        self,
        *,
        analysis_id: UUID,
        result: FinalAnalysisResponse,
    ) -> None:
        rows = [
            AnalysisContradiction(
                analysis_id=analysis_id,
                evidence_a_id=contradiction.evidence_a_id,
                evidence_b_id=contradiction.evidence_b_id,
                status=contradiction.status.value,
                contradiction_type=(
                    contradiction.contradiction_type.value
                ),
                score=float(contradiction.score),
                explanation=contradiction.explanation,
            )
            for contradiction in result.contradictions
        ]

        if rows:
            self._session.add_all(rows)

    @staticmethod
    def _build_final_answer(
        result: FinalAnalysisResponse,
    ) -> str:
        sections = (
            (
                "Military Analysis",
                result.military_analysis.analysis_text,
            ),
            (
                "Legal Analysis",
                result.legal_analysis.analysis_text,
            ),
            (
                "Historical Analysis",
                result.historical_analysis.analysis_text,
            ),
        )

        return "\n\n".join(
            f"{title}\n{text}"
            for title, text in sections
            if text and text.strip()
        )

    @staticmethod
    def _build_claim_perspectives(
        result: FinalAnalysisResponse,
    ) -> dict[str, str]:
        mapping: dict[str, str] = {}

        perspectives = (
            result.military_analysis,
            result.legal_analysis,
            result.historical_analysis,
        )

        for perspective_result in perspectives:
            perspective = perspective_result.perspective.value

            for claim in perspective_result.claims:
                normalized = AnalysisRepository._normalize_claim(
                    claim
                )

                if normalized:
                    mapping[normalized] = perspective

        return mapping

    @staticmethod
    def _normalize_claim(claim: str) -> str:
        return " ".join(claim.strip().lower().split())

    @staticmethod
    def _support_type(verdict: str) -> str:
        normalized = verdict.strip().lower()

        if normalized in {"supported", "verified"}:
            return "support"

        if normalized in {"refuted", "contradicted"}:
            return "refute"

        return "context"

    def get_analysis(
        self,
        analysis_id: UUID,
        *,
        user_id: UUID | None = None,
    ) -> Analysis | None:
        """Get one persisted analysis."""

        statement = select(Analysis).where(
            Analysis.id == analysis_id
        )

        if user_id is not None:
            statement = statement.join(
                Query,
                Analysis.query_id == Query.id,
            ).where(Query.user_id == user_id)

        return self._session.execute(
            statement
        ).scalar_one_or_none()

    def list_analyses(
        self,
        *,
        user_id: UUID,
    ) -> list[Analysis]:
        """Return the user's analysis history."""

        statement = (
            select(Analysis)
            .join(Query, Analysis.query_id == Query.id)
            .where(Query.user_id == user_id)
            .order_by(Analysis.completed_at.desc())
        )

        return list(
            self._session.execute(statement)
            .scalars()
            .all()
        )

    def delete_analysis(
        self,
        *,
        analysis_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Delete one analysis belonging to a specific user."""

        try:
            statement = (
                select(Analysis, Query)
                .join(
                    Query,
                    Analysis.query_id == Query.id,
                )
                .where(
                    Analysis.id == analysis_id,
                    Query.user_id == user_id,
                )
            )

            result = self._session.execute(
                statement
            ).one_or_none()

            if result is None:
                return False

            analysis, query = result

            # Delete analysis first.
            # Its child records use ON DELETE CASCADE.
            self._session.delete(analysis)
            self._session.flush()

            # Delete the corresponding query as well.
            self._session.delete(query)

            self._session.commit()

            return True

        except SQLAlchemyError as exc:
            self._session.rollback()

            raise RepositoryError(
                "Failed to delete analysis."
            ) from exc

    def get_perspectives(
        self,
        analysis_id: UUID,
    ) -> list[AnalysisPerspective]:
        """Return persisted perspective results."""

        statement = (
            select(AnalysisPerspective)
            .where(
                AnalysisPerspective.analysis_id == analysis_id
            )
            .order_by(AnalysisPerspective.perspective)
        )

        return list(
            self._session.execute(statement)
            .scalars()
            .all()
        )

    def get_evidence(
        self,
        analysis_id: UUID,
    ) -> list[AnalysisEvidenceRow]:
        """Return evidence snapshots for an analysis."""

        statement = (
            select(AnalysisEvidenceRow)
            .where(
                AnalysisEvidenceRow.analysis_id == analysis_id
            )
            .order_by(AnalysisEvidenceRow.id)
        )

        return list(
            self._session.execute(statement)
            .scalars()
            .all()
        )

    def get_claims(
        self,
        analysis_id: UUID,
    ) -> list[Claim]:
        """Return claims for an analysis."""

        statement = (
            select(Claim)
            .where(Claim.analysis_id == analysis_id)
            .order_by(Claim.id)
        )

        return list(
            self._session.execute(statement)
            .scalars()
            .all()
        )

    def get_contradictions(
        self,
        analysis_id: UUID,
    ) -> list[AnalysisContradiction]:
        """Return contradictions for an analysis."""

        statement = (
            select(AnalysisContradiction)
            .where(
                AnalysisContradiction.analysis_id == analysis_id
            )
            .order_by(AnalysisContradiction.id)
        )

        return list(
            self._session.execute(statement)
            .scalars()
            .all()
        )