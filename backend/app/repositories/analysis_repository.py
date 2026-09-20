"""Repository for MIL-EVID analysis persistence."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
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
    """Persist and retrieve MIL-EVID analysis results and execution state."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # =========================================================
    # CREATE PROCESSING ANALYSIS
    # =========================================================

    def create_processing_analysis(
        self,
        *,
        user_id: UUID,
        query_text: str,
        started_at: datetime | None = None,
    ) -> Analysis:
        """
        Create the analysis row before the pipeline starts.

        The existing Analysis.status column is used to store the
        current pipeline stage. No additional database columns are
        required.
        """

        try:
            query_record = Query(
                user_id=user_id,
                query_text=query_text,
            )

            self._session.add(query_record)
            self._session.flush()

            analysis_record = Analysis(
                query_id=query_record.id,
                status="q",
                final_answer="",
                overall_confidence=0,
                started_at=started_at,
                completed_at=None,
            )

            self._session.add(analysis_record)
            self._session.commit()
            self._session.refresh(analysis_record)

            return analysis_record

        except SQLAlchemyError as exc:
            self._session.rollback()

            raise RepositoryError(
                f"Failed to create processing analysis: {exc}"
            ) from exc

    # =========================================================
    # UPDATE ANALYSIS STATUS
    # =========================================================

    def update_analysis_status(
        self,
        *,
        analysis_id: UUID,
        status: str,
    ) -> Analysis | None:
        """
        Update the current execution stage of an analysis.

        Status values are intentionally short because the existing
        database column is String(20).
        """

        try:
            analysis = self._session.execute(
                select(Analysis).where(
                    Analysis.id == analysis_id
                )
            ).scalar_one_or_none()

            if analysis is None:
                return None

            analysis.status = status

            self._session.commit()
            self._session.refresh(analysis)

            return analysis

        except SQLAlchemyError as exc:
            self._session.rollback()

            raise RepositoryError(
                f"Failed to update analysis status: {exc}"
            ) from exc

    # =========================================================
    # MARK ANALYSIS AS FAILED
    # =========================================================

    def mark_analysis_failed(
        self,
        *,
        analysis_id: UUID,
    ) -> Analysis | None:
        """Mark an analysis as failed."""

        try:
            analysis = self._session.execute(
                select(Analysis).where(
                    Analysis.id == analysis_id
                )
            ).scalar_one_or_none()

            if analysis is None:
                return None

            analysis.status = "failed"

            self._session.commit()
            self._session.refresh(analysis)

            return analysis

        except SQLAlchemyError as exc:
            self._session.rollback()

            raise RepositoryError(
                f"Failed to mark analysis as failed: {exc}"
            ) from exc

    # =========================================================
    # COMPLETE ANALYSIS
    # =========================================================

    def complete_analysis(
        self,
        *,
        analysis_id: UUID,
        result: FinalAnalysisResponse,
        evidence: Sequence[AnalysisEvidence],
        completed_at: datetime | None = None,
    ) -> Analysis:
        """
        Persist the completed analysis into the existing analysis row.

        This is intentionally separate from create_processing_analysis()
        so the same database record is used throughout the lifecycle.
        """

        try:
            analysis_record = self._session.execute(
                select(Analysis).where(
                    Analysis.id == analysis_id
                )
            ).scalar_one_or_none()

            if analysis_record is None:
                raise RepositoryError(
                    f"Analysis {analysis_id} not found."
                )

            analysis_record.status = "completed"

            analysis_record.final_answer = (
                self._build_final_answer(result)
            )

            analysis_record.overall_confidence = float(
                result.confidence.final_score
            )

            analysis_record.completed_at = completed_at

            # -------------------------------------------------
            # Perspectives
            # -------------------------------------------------

            self._add_perspectives(
                analysis_id=analysis_id,
                result=result,
            )

            # -------------------------------------------------
            # Evidence
            # -------------------------------------------------

            evidence_map = self._add_evidence(
                analysis_id=analysis_id,
                evidence=evidence,
            )

            # -------------------------------------------------
            # Claims
            # -------------------------------------------------

            self._add_claims(
                analysis_id=analysis_id,
                result=result,
                evidence_map=evidence_map,
            )

            # -------------------------------------------------
            # Contradictions
            # -------------------------------------------------

            self._add_contradictions(
                analysis_id=analysis_id,
                result=result,
            )

            self._session.commit()
            self._session.refresh(analysis_record)

            return analysis_record

        except RepositoryError:
            self._session.rollback()
            raise

        except SQLAlchemyError as exc:
            self._session.rollback()

            raise RepositoryError(
                f"Failed to persist completed analysis: {exc}"
            ) from exc

    # =========================================================
    # LEGACY COMPATIBILITY METHOD
    # =========================================================

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
        """
        Compatibility method for callers that still expect the old
        single-step create_analysis() behavior.

        New analysis flows should use:

            create_processing_analysis()
            ...
            complete_analysis()

        This method intentionally preserves the old behavior.
        """

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

    # =========================================================
    # PERSPECTIVES
    # =========================================================

    def _add_perspectives(
        self,
        *,
        analysis_id: UUID,
        result: FinalAnalysisResponse,
    ) -> None:
        """Persist the three perspective outputs."""

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

    # =========================================================
    # EVIDENCE
    # =========================================================

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

    # =========================================================
    # CLAIMS
    # =========================================================

    def _add_claims(
        self,
        *,
        analysis_id: UUID,
        result: FinalAnalysisResponse,
        evidence_map: dict[str, UUID],
    ) -> None:
        """Persist claims and their evidence relationships."""

        perspective_by_claim = self._build_claim_perspectives(
            result
        )

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
                support_score=float(
                    verification.support_score
                ),
                verified=verification.verified,
            )

            self._session.add(claim_record)
            self._session.flush()

            relationships: list[ClaimEvidence] = []

            for evidence_id in (
                verification.supporting_evidence_ids
            ):
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
                self._session.add_all(
                    relationships
                )

    # =========================================================
    # CONTRADICTIONS
    # =========================================================

    def _add_contradictions(
        self,
        *,
        analysis_id: UUID,
        result: FinalAnalysisResponse,
    ) -> None:
        """Persist detected contradictions."""

        rows = [
            AnalysisContradiction(
                analysis_id=analysis_id,
                evidence_a_id=contradiction.evidence_a_id,
                evidence_b_id=contradiction.evidence_b_id,
                status=contradiction.status.value,
                contradiction_type=(
                    contradiction.contradiction_type.value
                ),
                score=float(
                    contradiction.score
                ),
                explanation=contradiction.explanation,
            )
            for contradiction in result.contradictions
        ]

        if rows:
            self._session.add_all(rows)

    # =========================================================
    # FINAL ANSWER
    # =========================================================

    @staticmethod
    def _build_final_answer(
        result: FinalAnalysisResponse,
    ) -> str:
        """Build the persisted final answer."""

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

    # =========================================================
    # CLAIM → PERSPECTIVE MAPPING
    # =========================================================

    @staticmethod
    def _build_claim_perspectives(
        result: FinalAnalysisResponse,
    ) -> dict[str, str]:
        """Map normalized claims to their perspective."""

        mapping: dict[str, str] = {}

        perspectives = (
            result.military_analysis,
            result.legal_analysis,
            result.historical_analysis,
        )

        for perspective_result in perspectives:
            perspective = (
                perspective_result.perspective.value
            )

            for claim in perspective_result.claims:
                normalized = (
                    AnalysisRepository._normalize_claim(
                        claim
                    )
                )

                if normalized:
                    mapping[normalized] = perspective

        return mapping

    # =========================================================
    # CLAIM NORMALIZATION
    # =========================================================

    @staticmethod
    def _normalize_claim(claim: str) -> str:
        return " ".join(
            claim.strip().lower().split()
        )

    # =========================================================
    # CLAIM SUPPORT TYPE
    # =========================================================

    @staticmethod
    def _support_type(verdict: str) -> str:
        normalized = verdict.strip().lower()

        if normalized in {
            "supported",
            "verified",
        }:
            return "support"

        if normalized in {
            "refuted",
            "contradicted",
        }:
            return "refute"

        return "context"

    # =========================================================
    # GET ONE ANALYSIS
    # =========================================================

    def get_analysis(
        self,
        analysis_id: UUID,
        *,
        user_id: UUID | None = None,
    ) -> Analysis | None:
        """Get one analysis."""

        statement = select(Analysis).where(
            Analysis.id == analysis_id
        )

        if user_id is not None:
            statement = statement.join(
                Query,
                Analysis.query_id == Query.id,
            ).where(
                Query.user_id == user_id
            )

        return self._session.execute(
            statement
        ).scalar_one_or_none()

    # =========================================================
    # LIST ANALYSES
    # =========================================================

    def list_analyses(
        self,
        *,
        user_id: UUID,
    ) -> list[tuple[Analysis, Query, int]]:
        """Return the user's analysis history."""

        evidence_count = (
            select(
                func.count(
                    AnalysisEvidenceRow.id
                )
            )
            .where(
                AnalysisEvidenceRow.analysis_id
                == Analysis.id
            )
            .correlate(Analysis)
            .scalar_subquery()
        )

        statement = (
            select(
                Analysis,
                Query,
                evidence_count.label(
                    "evidence_count"
                ),
            )
            .join(
                Query,
                Analysis.query_id == Query.id,
            )
            .where(
                Query.user_id == user_id
            )
            .order_by(
                Analysis.completed_at.desc().nullslast(),
                Analysis.id.desc(),
            )
        )

        return list(
            self._session.execute(
                statement
            ).all()
        )

    # =========================================================
    # DELETE ANALYSIS
    # =========================================================

    def delete_analysis(
        self,
        *,
        analysis_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Delete one analysis belonging to the user."""

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

            # Child analysis records use ON DELETE CASCADE.
            self._session.delete(analysis)
            self._session.flush()

            # Query is not needed after the analysis is deleted.
            self._session.delete(query)

            self._session.commit()

            return True

        except SQLAlchemyError as exc:
            self._session.rollback()

            raise RepositoryError(
                "Failed to delete analysis."
            ) from exc

    # =========================================================
    # PERSPECTIVE RESULTS
    # =========================================================

    def get_perspectives(
        self,
        analysis_id: UUID,
    ) -> list[AnalysisPerspective]:
        """Return persisted perspective results."""

        statement = (
            select(AnalysisPerspective)
            .where(
                AnalysisPerspective.analysis_id
                == analysis_id
            )
            .order_by(
                AnalysisPerspective.perspective
            )
        )

        return list(
            self._session.execute(
                statement
            )
            .scalars()
            .all()
        )

    # =========================================================
    # ANALYSIS EVIDENCE
    # =========================================================

    def get_evidence(
        self,
        analysis_id: UUID,
    ) -> list[AnalysisEvidenceRow]:
        """Return evidence snapshots for an analysis."""

        statement = (
            select(AnalysisEvidenceRow)
            .where(
                AnalysisEvidenceRow.analysis_id
                == analysis_id
            )
            .order_by(
                AnalysisEvidenceRow.id
            )
        )

        return list(
            self._session.execute(
                statement
            )
            .scalars()
            .all()
        )

    # =========================================================
    # CLAIMS
    # =========================================================

    def get_claims(
        self,
        analysis_id: UUID,
    ) -> list[Claim]:
        """Return claims for an analysis."""

        statement = (
            select(Claim)
            .where(
                Claim.analysis_id == analysis_id
            )
            .order_by(Claim.id)
        )

        return list(
            self._session.execute(
                statement
            )
            .scalars()
            .all()
        )

    # =========================================================
    # CONTRADICTIONS
    # =========================================================

    def get_contradictions(
        self,
        analysis_id: UUID,
    ) -> list[AnalysisContradiction]:
        """Return contradictions for an analysis."""

        statement = (
            select(AnalysisContradiction)
            .where(
                AnalysisContradiction.analysis_id
                == analysis_id
            )
            .order_by(
                AnalysisContradiction.id
            )
        )

        return list(
            self._session.execute(
                statement
            )
            .scalars()
            .all()
        )

    # =========================================================
    # QUERY
    # =========================================================

    def get_query_for_analysis(
        self,
        analysis_id: UUID,
        *,
        user_id: UUID,
    ) -> Query | None:
        """Return the query belonging to an analysis."""

        statement = (
            select(Query)
            .join(
                Analysis,
                Analysis.query_id == Query.id,
            )
            .where(
                Analysis.id == analysis_id,
                Query.user_id == user_id,
            )
        )

        return self._session.execute(
            statement
        ).scalar_one_or_none()