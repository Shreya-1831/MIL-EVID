from app.domain.models.analysis import AnalysisEvidence
from app.modules.analysis.evidence_guard import EvidenceConsistencyGuard


def make_evidence(
    *,
    evidence_id: str,
    title: str,
    text: str,
) -> AnalysisEvidence:
    return AnalysisEvidence(
        evidence_id=evidence_id,
        text=text,
        source="test",
        source_type="ucdp",
        perspective="military",
        title=title,
        date=None,
        url=None,
        document_id="doc-1",
        chunk_index=0,
        reranker_score=1.0,
        original_rrf_score=1.0,
        ranks=(),
    )


def test_matching_country_evidence_is_direct():
    guard = EvidenceConsistencyGuard()

    evidence = (
        make_evidence(
            evidence_id="1",
            title="India Pakistan border",
            text="India and Pakistan agreed to maintain the ceasefire.",
        ),
    )

    result = guard.filter(
        query="India Pakistan border escalation",
        evidence=evidence,
    )

    assert len(result.direct_evidence) == 1
    assert len(result.contextual_evidence) == 0


def test_different_country_evidence_is_contextual():
    guard = EvidenceConsistencyGuard()

    evidence = (
        make_evidence(
            evidence_id="1",
            title="India China agreement",
            text="India and China established confidence building measures.",
        ),
    )

    result = guard.filter(
        query="India Pakistan border escalation",
        evidence=evidence,
    )

    assert len(result.direct_evidence) == 0
    assert len(result.contextual_evidence) == 1


def test_evidence_without_identifiable_country_is_contextual():
    guard = EvidenceConsistencyGuard()

    evidence = (
        make_evidence(
            evidence_id="1",
            title="Military deployment",
            text="Forces were deployed near the border.",
        ),
    )

    result = guard.filter(
        query="India Pakistan border escalation",
        evidence=evidence,
    )

    assert len(result.direct_evidence) == 0
    assert len(result.contextual_evidence) == 1