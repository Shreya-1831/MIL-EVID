from unittest.mock import Mock

from app.domain.enums import Perspective, SourceType
from app.domain.models.analysis import (
    AnalysisEvidence,
    EvidenceContext,
)
from app.modules.analysis.analyzer import EvidenceAnalyzer


def make_context() -> EvidenceContext:
    evidence = AnalysisEvidence(
        evidence_id="chunk-001",
        text="Armed forces conducted military operations.",
        source="UCDP",
        source_type=SourceType.UCDP,
        perspective=Perspective.MILITARY,
        reranker_score=0.95,
        original_rrf_score=0.03,
        ranks=(1, 2),
    )

    return EvidenceContext(
        query="What happened during the conflict?",
        evidence=(evidence,),
    )


def test_analyzer_returns_three_perspectives() -> None:
    llm = Mock()
    llm.generate.return_value = "Evidence-grounded analysis."

    analyzer = EvidenceAnalyzer(llm)

    military, legal, historical = analyzer.analyze(
        context=make_context(),
    )

    assert military.perspective == Perspective.MILITARY
    assert legal.perspective == Perspective.LEGAL
    assert historical.perspective == Perspective.HISTORICAL

    assert military.analysis_text == "Evidence-grounded analysis."
    assert legal.analysis_text == "Evidence-grounded analysis."
    assert historical.analysis_text == "Evidence-grounded analysis."

    assert llm.generate.call_count == 3


def test_analyzer_preserves_evidence_ids() -> None:
    llm = Mock()
    llm.generate.return_value = "Analysis."

    analyzer = EvidenceAnalyzer(llm)

    military, _, _ = analyzer.analyze(
        context=make_context(),
    )

    assert military.evidence_ids == ("chunk-001",)


def test_analyzer_uses_perspective_specific_prompts() -> None:
    llm = Mock()
    llm.generate.return_value = "Analysis."

    analyzer = EvidenceAnalyzer(llm)

    analyzer.analyze(context=make_context())

    calls = llm.generate.call_args_list

    prompts = [
        call.kwargs["system_prompt"]
        for call in calls
    ]

    assert "military" in prompts[0].lower()
    assert "legal" in prompts[1].lower()
    assert "historical" in prompts[2].lower()


def test_analyzer_passes_query_and_evidence_to_llm() -> None:
    llm = Mock()
    llm.generate.return_value = "Analysis."

    analyzer = EvidenceAnalyzer(llm)

    analyzer.analyze(context=make_context())

    call = llm.generate.call_args

    user_prompt = call.kwargs["user_prompt"]

    assert "What happened during the conflict?" in user_prompt
    assert "chunk-001" in user_prompt
    assert "Armed forces conducted military operations." in user_prompt