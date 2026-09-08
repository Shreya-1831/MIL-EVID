from unittest.mock import Mock

from app.domain.enums import Perspective, SourceType
from app.domain.models.analysis import (
    AnalysisEvidence,
    EvidenceContext,
)
from app.modules.retrieval.hybrid_retriever import HybridSearchResult
from app.modules.retrieval.reranker import RerankedSearchResult
from app.services.analysis_service import AnalysisService


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

    service = AnalysisService(
        retriever=retriever,
        reranker=reranker,
        context_builder=context_builder,
        analyzer=analyzer,
        evidence_guard=evidence_guard,
    )

    return service, {
        "retriever": retriever,
        "reranker": reranker,
        "context_builder": context_builder,
        "analyzer": analyzer,
        "evidence_guard": evidence_guard,
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

    expected = (
        Mock(),
        Mock(),
        Mock(),
    )
    mocks["analyzer"].analyze.return_value = expected

    result = service.analyze(
        query="What happened?",
    )

    assert result == expected

    mocks["analyzer"].analyze.assert_called_once()

    analyzed_context = mocks["analyzer"].analyze.call_args.kwargs["context"]

    assert analyzed_context.query == context.query
    assert analyzed_context.evidence == context.evidence


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
    assert result.direct_evidence_ids == ("chunk-001",)
    assert result.contextual_evidence_ids == ()

    mocks["retriever"].search.assert_called_once_with(
        "What happened?",
        top_k=10,
    )

    mocks["reranker"].rerank.assert_called_once_with(
        query="What happened?",
        candidates=[hybrid_result],
        chunk_texts={
            "chunk-001": "Military forces conducted operations.",
        },
        top_k=5,
    )

    mocks["context_builder"].build.assert_called_once_with(
        query="What happened?",
        reranked_results=[reranked_result],
    )

    mocks["evidence_guard"].filter.assert_called_once_with(
        query="What happened?",
        evidence=context.evidence,
    )