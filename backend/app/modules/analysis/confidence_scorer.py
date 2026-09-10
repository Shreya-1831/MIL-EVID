"""Confidence scoring for evidence-grounded analysis."""

from __future__ import annotations

from datetime import datetime, timezone

from app.domain.enums import ConfidenceLevel
from app.domain.models.analysis import (
    AnalysisEvidence,
    ClaimVerificationResult,
    ConfidenceResult,
    ContradictionResult,
)


class ConfidenceScorer:
    """Calculate an explainable confidence score."""

    SOURCE_RELIABILITY = {
        "ucdp": 90.0,
        "sipri": 90.0,
        "icrc_ihl": 95.0,
        "un_peacemaker": 90.0,
        "acled": 85.0,
    }

    def score(
        self,
        *,
        evidence: tuple[AnalysisEvidence, ...],
        contradictions: tuple[ContradictionResult, ...] = (),
        claim_verification: tuple[ClaimVerificationResult, ...] = (),
    ) -> ConfidenceResult:
        """Calculate confidence from evidence and verification signals."""

        relevance_score = self._relevance_score(evidence)
        agreement_score = self._agreement_score(contradictions)
        freshness_score = self._freshness_score(evidence)
        source_reliability_score = self._source_reliability_score(evidence)
        claim_support_score = self._claim_support_score(
            claim_verification
        )

        final_score = (
            relevance_score * 0.25
            + agreement_score * 0.20
            + freshness_score * 0.15
            + source_reliability_score * 0.20
            + claim_support_score * 0.20
        )

        confidence_level = self._confidence_level(final_score)

        return ConfidenceResult(
            relevance_score=round(relevance_score, 2),
            agreement_score=round(agreement_score, 2),
            freshness_score=round(freshness_score, 2),
            source_reliability_score=round(
                source_reliability_score,
                2,
            ),
            claim_support_score=round(
                claim_support_score,
                2,
            ),
            final_score=round(final_score, 2),
            confidence_level=confidence_level,
        )

    @staticmethod
    def _relevance_score(
        evidence: tuple[AnalysisEvidence, ...],
    ) -> float:
        """Estimate retrieval relevance from cross-encoder scores."""

        if not evidence:
            return 0.0

        scores = [item.reranker_score for item in evidence]

        # Cross-encoder scores can be outside the [0, 1] range.
        # If the scores already look like normalized relevance values,
        # preserve their original meaning.
        if all(0.0 <= score <= 1.0 for score in scores):
            return sum(scores) / len(scores) * 100.0

        # For raw cross-encoder scores, normalize them across the
        # retrieved evidence set.
        minimum = min(scores)
        maximum = max(scores)

        if maximum == minimum:
            # With one/all-identical raw scores, treat the evidence as
            # moderately relevant rather than claiming maximum relevance.
            return 50.0

        normalized_scores = [
            (score - minimum) / (maximum - minimum)
            for score in scores
        ]

        return sum(normalized_scores) / len(normalized_scores) * 100.0

    @staticmethod
    def _agreement_score(
        contradictions: tuple[ContradictionResult, ...],
    ) -> float:
        """Estimate evidence agreement from contradiction results."""
        if not contradictions:
            return 100.0

        weighted_scores: list[float] = []

        for result in contradictions:
            if result.status.value == "contradiction":
                # Strong contradiction -> low agreement.
                weighted_scores.append(
                    (1.0 - result.score) * 100.0
                )

            elif result.status.value == "entailment":
                # Strong entailment -> high agreement.
                weighted_scores.append(
                    result.score * 100.0
                )

            else:
                # Neutral means no contradiction was established.
                # Do not penalize confidence as if disagreement exists.
                weighted_scores.append(100.0)

        return sum(weighted_scores) / len(weighted_scores)

    @classmethod
    def _source_reliability_score(
        cls,
        evidence: tuple[AnalysisEvidence, ...],
    ) -> float:
        """Estimate reliability from configured source scores."""

        if not evidence:
            return 0.0

        scores = [
            cls.SOURCE_RELIABILITY.get(
                item.source_type.value,
                50.0,
            )
            for item in evidence
        ]

        return sum(scores) / len(scores)

    @staticmethod
    def _freshness_score(
        evidence: tuple[AnalysisEvidence, ...],
    ) -> float:
        """Estimate freshness using evidence dates."""

        if not evidence:
            return 0.0

        now = datetime.now(timezone.utc)

        scores: list[float] = []

        for item in evidence:
            if item.date is None:
                scores.append(50.0)
                continue

            evidence_date = item.date

            if evidence_date.tzinfo is None:
                evidence_date = evidence_date.replace(
                    tzinfo=timezone.utc
                )

            age_days = max(
                0,
                (now - evidence_date).days,
            )

            if age_days <= 30:
                score = 100.0
            elif age_days <= 180:
                score = 85.0
            elif age_days <= 365:
                score = 70.0
            elif age_days <= 3 * 365:
                score = 50.0
            else:
                score = 30.0

            scores.append(score)

        return sum(scores) / len(scores)

    @staticmethod
    def _claim_support_score(
        claims: tuple[ClaimVerificationResult, ...],
    ) -> float:
        """Calculate confidence from claim verification."""

        if not claims:
            return 50.0

        return (
            sum(
                claim.support_score
                for claim in claims
            )
            / len(claims)
            * 100.0
        )

    @staticmethod
    def _confidence_level(
        score: float,
    ) -> ConfidenceLevel:
        """Map final score to a confidence level."""

        if score >= 75.0:
            return ConfidenceLevel.HIGH

        if score >= 50.0:
            return ConfidenceLevel.MEDIUM

        return ConfidenceLevel.LOW