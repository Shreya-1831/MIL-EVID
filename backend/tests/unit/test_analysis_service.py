from unittest.mock import Mock

from app.domain.enums import Perspective, SourceType
from app.domain.models.analysis import (
    AnalysisEvidence,
    ConfidenceResult,
    EvidenceContext,
    PerspectiveAnalysisResult,
    Citation,
)
from app.modules.retrieval.hybrid_retriever import HybridSearchResult
from app.modules.retrieval.reranker import RerankedSearchResult
from app.services.analysis_service import AnalysisService
from app.modules.analysis.perspective_selector import (
    PerspectiveAwareCandidateSelector,
)
from app.modules.analysis.post_rerank_perspective_selector import (
    PostRerankPerspectiveSelector,
)

def make_context() -> EvidenceContext:
    evidence = AnalysisEvidence(
        evidence_id="chunk-001",
        text="Military forces conducted operations.",
        source="UCDP",
        source_type=SourceType.UCDP,
        perspective=Perspective.MILITARY,
        reranker_score=0.9,
        original_rrf_score=0.03,
        ranks=(1,),
    )

    return EvidenceContext(
        query="What happened?",
        evidence=(evidence,),
    )


def make_service() -> tuple[AnalysisService, dict]:
    retriever = Mock()
    reranker = Mock()
    context_builder = Mock()
    analyzer = Mock()
    evidence_guard = Mock()
    contradiction_detector = Mock()
    confidence_scorer = Mock()
    claim_verifier = Mock()

    contradiction_detector.detect.return_value = ()
    claim_verifier.verify.return_value = ()

    confidence = ConfidenceResult(
        relevance_score=90.0,
        agreement_score=100.0,
        freshness_score=50.0,
        source_reliability_score=90.0,
        claim_support_score=50.0,
        final_score=76.0,
        confidence_level="high",
    )

    confidence_scorer.score.return_value = confidence

    service = AnalysisService(
        retriever=retriever,
        reranker=reranker,
        context_builder=context_builder,
        analyzer=analyzer,
        evidence_guard=evidence_guard,
        contradiction_detector=contradiction_detector,
        confidence_scorer=confidence_scorer,
        claim_verifier=claim_verifier,
        perspective_selector=PerspectiveAwareCandidateSelector(),
        post_rerank_perspective_selector=PostRerankPerspectiveSelector(),
    )

    return service, {
        "retriever": retriever,
        "reranker": reranker,
        "context_builder": context_builder,
        "analyzer": analyzer,
        "evidence_guard": evidence_guard,
        "contradiction_detector": contradiction_detector,
        "confidence_scorer": confidence_scorer,
        "claim_verifier": claim_verifier,
    }


def test_build_context_returns_empty_context_when_no_results() -> None:
    service, mocks = make_service()

    mocks["retriever"].search.return_value = []

    mocks["context_builder"].build.return_value = EvidenceContext(
        query="What happened?",
        evidence=(),
    )

    result = service.build_context(
        query="What happened?",
    )

    assert result.query == "What happened?"
    assert result.evidence == ()

    mocks["reranker"].rerank.assert_not_called()
    mocks["evidence_guard"].filter.assert_not_called()


def test_analyze_passes_context_to_analyzer() -> None:
    service, mocks = make_service()

    mocks["retriever"].search.return_value = []

    context = make_context()
    mocks["context_builder"].build.return_value = context

    military = PerspectiveAnalysisResult(
        perspective=Perspective.MILITARY,
        analysis_text="Military analysis.",
    )

    legal = PerspectiveAnalysisResult(
        perspective=Perspective.LEGAL,
        analysis_text="Legal analysis.",
    )

    historical = PerspectiveAnalysisResult(
        perspective=Perspective.HISTORICAL,
        analysis_text="Historical analysis.",
    )

    mocks["analyzer"].analyze.return_value = (
        military,
        legal,
        historical,
    )

    contradictions = ()
    mocks["contradiction_detector"].detect.return_value = contradictions

    confidence = mocks["confidence_scorer"].score.return_value

    result = service.analyze(
        query="What happened?",
    )

    assert result.query.raw_query == "What happened?"
    assert result.query.normalized_query == "What happened?"

    assert result.military_analysis is military
    assert result.legal_analysis is legal
    assert result.historical_analysis is historical

    assert result.contradictions == ()
    assert result.claim_verification == ()
    assert result.confidence is confidence
    assert result.citations == ()

    mocks["analyzer"].analyze.assert_called_once()

    analyzed_context = (
        mocks["analyzer"]
        .analyze
        .call_args
        .kwargs["context"]
    )

    assert analyzed_context.query == context.query
    assert analyzed_context.evidence == context.evidence

    mocks["contradiction_detector"].detect.assert_called_once_with(
        evidence=context.evidence,
    )

    mocks["claim_verifier"].verify.assert_called_once_with(
        claims=(),
        evidence=context.evidence,
    )

    mocks["confidence_scorer"].score.assert_called_once_with(
        evidence=context.evidence,
        contradictions=contradictions,
        claim_verification=(),
    )


def test_build_context_runs_retrieval_and_reranking() -> None:
    service, mocks = make_service()

    hybrid_result = HybridSearchResult(
        chunk_id="chunk-001",
        score=0.03,
        ranks=(1, 2),
    )

    reranked_result = RerankedSearchResult(
        chunk_id="chunk-001",
        score=0.95,
        original_rrf_score=0.03,
        ranks=(1, 2),
    )

    mocks["retriever"].search.return_value = [
        hybrid_result,
    ]

    mocks["reranker"].rerank.return_value = [
        reranked_result,
    ]

    context = make_context()
    mocks["context_builder"].build.return_value = context

    # Make the guard pass the evidence through unchanged.
    guard_result = Mock()
    guard_result.direct_evidence = context.evidence
    guard_result.contextual_evidence = ()

    mocks["evidence_guard"].filter.return_value = guard_result

    # Avoid filesystem access in this orchestration test.
    service._resolve_chunk_texts = Mock(
        return_value={
            "chunk-001": "Military forces conducted operations.",
        }
    )

    result = service.build_context(
        query="What happened?",
        retrieval_top_k=10,
        rerank_top_k=5,
    )

    assert result.query == context.query
    assert result.evidence == context.evidence

    assert result.direct_evidence_ids == (
        "chunk-001",
    )

    assert result.contextual_evidence_ids == ()

    mocks["retriever"].search.assert_called_once_with(
        "What happened?",
        top_k=10,
    )

    mocks["reranker"].rerank.assert_called_once()

    rerank_call = mocks["reranker"].rerank.call_args

    assert rerank_call.kwargs["query"] == "What happened?"
    assert rerank_call.kwargs["candidates"] == (hybrid_result,)
    assert rerank_call.kwargs["chunk_texts"] == {
        "chunk-001": "Military forces conducted operations."
    }
    assert rerank_call.kwargs["top_k"] == 1

    mocks["context_builder"].build.assert_called_once_with(
        query="What happened?",
        reranked_results=[reranked_result],
    )

    mocks["evidence_guard"].filter.assert_called_once_with(
        query="What happened?",
        evidence=context.evidence,
    )


def test_collect_citations_deduplicates_by_evidence_id() -> None:
    citation_a = Citation(
        evidence_id="chunk-001",
        source="UCDP",
        title="UCDP Evidence",
        url="https://example.com/ucdp",
    )

    citation_b = Citation(
        evidence_id="chunk-002",
        source="UN Peacemaker",
        title="UN Evidence",
        url="https://example.com/un",
    )

    military = PerspectiveAnalysisResult(
        perspective=Perspective.MILITARY,
        analysis_text="Military analysis.",
        citations=(citation_a, citation_b),
    )

    legal = PerspectiveAnalysisResult(
        perspective=Perspective.LEGAL,
        analysis_text="Legal analysis.",
        citations=(citation_a,),
    )

    historical = PerspectiveAnalysisResult(
        perspective=Perspective.HISTORICAL,
        analysis_text="Historical analysis.",
        citations=(citation_b,),
    )

    citations = AnalysisService._collect_citations(
        military=military,
        legal=legal,
        historical=historical,
    )

    assert len(citations) == 2
    assert citations[0].evidence_id == "chunk-001"
    assert citations[1].evidence_id == "chunk-002"