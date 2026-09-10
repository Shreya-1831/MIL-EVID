from datetime import datetime, timezone

from app.domain.enums import (
    ClaimVerificationStatus,
    ConfidenceLevel,
    ContradictionStatus,
    ContradictionType,
    Perspective,
    SourceType,
)
from app.domain.models.analysis import (
    AnalysisEvidence,
    ClaimVerificationResult,
    ContradictionResult,
)
from app.modules.analysis.confidence_scorer import (
    ConfidenceScorer,
)


def make_evidence(
    evidence_id: str = "e1",
    score: float = 0.9,
    source_type: SourceType = SourceType.UCDP,
    date: datetime | None = None,
) -> AnalysisEvidence:
    return AnalysisEvidence(
        evidence_id=evidence_id,
        text="Military forces conducted operations.",
        source="Test",
        source_type=source_type,
        perspective=Perspective.MILITARY,
        reranker_score=score,
        original_rrf_score=0.03,
        ranks=(1,),
        date=date,
    )


def test_high_quality_evidence_produces_high_confidence() -> None:
    scorer = ConfidenceScorer()

    evidence = (
        make_evidence(
            score=1.0,
            source_type=SourceType.ICRC_IHL,
            date=datetime.now(timezone.utc),
        ),
    )

    result = scorer.score(evidence=evidence)

    assert result.relevance_score == 100.0
    assert result.freshness_score == 100.0
    assert result.source_reliability_score == 95.0
    assert result.confidence_level == ConfidenceLevel.HIGH


def test_empty_evidence_produces_low_confidence() -> None:
    scorer = ConfidenceScorer()

    result = scorer.score(evidence=())

    assert result.relevance_score == 0.0
    assert result.agreement_score == 100.0
    assert result.freshness_score == 0.0
    assert result.source_reliability_score == 0.0
    assert result.confidence_level == ConfidenceLevel.LOW


def test_contradiction_reduces_agreement() -> None:
    scorer = ConfidenceScorer()

    contradictions = (
        ContradictionResult(
            evidence_a_id="e1",
            evidence_b_id="e2",
            status=ContradictionStatus.CONTRADICTION,
            contradiction_type=ContradictionType.FACTUAL,
            score=1.0,
            explanation="The evidence conflicts.",
        ),
    )

    result = scorer.score(
        evidence=(make_evidence(),),
        contradictions=contradictions,
    )

    assert result.agreement_score == 0.0


def test_entailment_improves_agreement() -> None:
    scorer = ConfidenceScorer()

    contradictions = (
        ContradictionResult(
            evidence_a_id="e1",
            evidence_b_id="e2",
            status=ContradictionStatus.ENTAILMENT,
            contradiction_type=ContradictionType.NONE,
            score=0.9,
            explanation="The evidence agrees.",
        ),
    )

    result = scorer.score(
        evidence=(make_evidence(),),
        contradictions=contradictions,
    )

    assert result.agreement_score == 90.0


def test_supported_claims_raise_claim_support_score() -> None:
    scorer = ConfidenceScorer()

    claims = (
        ClaimVerificationResult(
            claim="The forces conducted operations.",
            supporting_evidence_ids=("e1",),
            support_score=0.95,
            status=ClaimVerificationStatus.SUPPORTED,
            verified=True,
        ),
    )

    result = scorer.score(
        evidence=(make_evidence(),),
        claim_verification=claims,
    )

    assert result.claim_support_score == 95.0


def test_unknown_date_gets_neutral_freshness() -> None:
    scorer = ConfidenceScorer()

    result = scorer.score(
        evidence=(
            make_evidence(date=None),
        ),
    )

    assert result.freshness_score == 50.0


def test_old_evidence_has_lower_freshness() -> None:
    scorer = ConfidenceScorer()

    old_date = datetime(
        2020,
        1,
        1,
        tzinfo=timezone.utc,
    )

    result = scorer.score(
        evidence=(
            make_evidence(date=old_date),
        ),
    )

    assert result.freshness_score == 30.0


def test_multiple_evidence_items_are_averaged() -> None:
    scorer = ConfidenceScorer()

    evidence = (
        make_evidence(
            evidence_id="e1",
            score=1.0,
        ),
        make_evidence(
            evidence_id="e2",
            score=0.5,
        ),
    )

    result = scorer.score(evidence=evidence)

    assert result.relevance_score == 75.0


def test_final_score_is_bounded() -> None:
    scorer = ConfidenceScorer()

    result = scorer.score(
        evidence=(
            make_evidence(
                score=1.0,
                source_type=SourceType.ICRC_IHL,
                date=datetime.now(timezone.utc),
            ),
        ),
    )

    assert 0.0 <= result.final_score <= 100.0