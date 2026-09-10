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


def make_grounded_context() -> EvidenceContext:
    direct_evidence = AnalysisEvidence(
        evidence_id="direct-001",
        text="India and Pakistan agreed to maintain the ceasefire.",
        source="UCDP",
        source_type=SourceType.UCDP,
        perspective=Perspective.MILITARY,
        reranker_score=0.95,
        original_rrf_score=0.03,
        ranks=(1,),
    )

    contextual_evidence = AnalysisEvidence(
        evidence_id="context-001",
        text="India and China established confidence building measures.",
        source="UN Peacemaker",
        source_type=SourceType.UN_PEACEMAKER,
        perspective=Perspective.HISTORICAL,
        reranker_score=0.80,
        original_rrf_score=0.02,
        ranks=(2,),
    )

    return EvidenceContext(
        query="India Pakistan border escalation",
        evidence=(
            direct_evidence,
            contextual_evidence,
        ),
        direct_evidence_ids=("direct-001",),
        contextual_evidence_ids=("context-001",),
    )


def make_llm() -> Mock:
    llm = Mock()

    llm.generate_structured.return_value = {
        "analysis": "Evidence-grounded analysis.",
        "claims": [
            "Armed forces conducted military operations.",
        ],
    }

    return llm


def test_analyzer_returns_three_perspectives() -> None:
    llm = make_llm()

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

    assert llm.generate_structured.call_count == 3


def test_analyzer_preserves_evidence_ids() -> None:
    llm = make_llm()

    analyzer = EvidenceAnalyzer(llm)

    military, _, _ = analyzer.analyze(
        context=make_context(),
    )

    assert military.evidence_ids == ("chunk-001",)


def test_analyzer_uses_perspective_specific_prompts() -> None:
    llm = make_llm()

    analyzer = EvidenceAnalyzer(llm)

    analyzer.analyze(context=make_context())

    calls = llm.generate_structured.call_args_list

    prompts = [
        call.kwargs["system_prompt"]
        for call in calls
    ]

    assert "military" in prompts[0].lower()
    assert "legal" in prompts[1].lower()
    assert "historical" in prompts[2].lower()


def test_analyzer_passes_query_and_evidence_to_llm() -> None:
    llm = make_llm()

    analyzer = EvidenceAnalyzer(llm)

    analyzer.analyze(context=make_context())

    calls = llm.generate_structured.call_args_list

    military_prompt = calls[0].kwargs["user_prompt"]

    assert "What happened during the conflict?" in military_prompt
    assert "chunk-001" in military_prompt
    assert "Armed forces conducted military operations." in military_prompt


def test_analyzer_labels_direct_and_contextual_evidence() -> None:
    llm = make_llm()

    analyzer = EvidenceAnalyzer(llm)

    analyzer.analyze(
        context=make_grounded_context(),
    )

    calls = llm.generate_structured.call_args_list

    military_prompt = calls[0].kwargs["user_prompt"]
    historical_prompt = calls[2].kwargs["user_prompt"]

    assert "DIRECT EVIDENCE" in military_prompt
    assert "direct-001" in military_prompt

    assert "CONTEXTUAL EVIDENCE" in historical_prompt
    assert "context-001" in historical_prompt

    assert "context-001" not in military_prompt
    assert "direct-001" not in historical_prompt


def test_analyzer_instructs_llm_not_to_transfer_cross_conflict_facts() -> None:
    llm = make_llm()

    analyzer = EvidenceAnalyzer(llm)

    analyzer.analyze(
        context=make_grounded_context(),
    )

    user_prompt = llm.generate_structured.call_args.kwargs[
        "user_prompt"
    ]

    prompt_lower = user_prompt.lower()

    assert "different country pair" in prompt_lower
    assert "conflict" in prompt_lower
    assert "do not transfer facts" in prompt_lower
    assert "contextual evidence" in prompt_lower


def test_user_prompt_blocks_cross_conflict_application() -> None:
    context = make_grounded_context()

    prompt = EvidenceAnalyzer._build_user_prompt(
        context=context,
        perspective=Perspective.MILITARY,
    )

    assert "different country pair" in prompt
    assert "must not" in prompt.lower()
    assert "applies to the queried situation" in prompt


def test_analyzer_populates_citations() -> None:
    llm = make_llm()

    analyzer = EvidenceAnalyzer(
        llm_client=llm,
    )

    evidence = AnalysisEvidence(
        evidence_id="evidence-1",
        text="A ceasefire agreement was announced.",
        source="UCDP",
        source_type=SourceType.UCDP,
        perspective=Perspective.MILITARY,
        title="Test Evidence",
        url="https://example.com/evidence-1",
        reranker_score=0.95,
        original_rrf_score=0.03,
        ranks=(1,),
    )

    context = EvidenceContext(
        query="Test query",
        evidence=(evidence,),
        direct_evidence_ids=("evidence-1",),
        contextual_evidence_ids=(),
    )

    military, legal, historical = analyzer.analyze(
        context=context,
    )

    assert len(military.citations) == 1

    citation = military.citations[0]

    assert citation.evidence_id == "evidence-1"
    assert citation.source == "UCDP"
    assert citation.title == "Test Evidence"
    assert citation.url == "https://example.com/evidence-1"

    assert legal.citations == ()
    assert historical.citations == ()


def test_analyzer_prioritizes_matching_perspective_evidence() -> None:
    llm = make_llm()

    military_evidence = AnalysisEvidence(
        evidence_id="military-001",
        text="Military event evidence.",
        source="UCDP",
        source_type=SourceType.UCDP,
        perspective=Perspective.MILITARY,
        reranker_score=0.70,
        original_rrf_score=0.03,
        ranks=(1,),
    )

    legal_evidence = AnalysisEvidence(
        evidence_id="legal-001",
        text="Legal evidence.",
        source="ICRC Customary IHL",
        source_type=SourceType.ICRC_IHL,
        perspective=Perspective.LEGAL,
        reranker_score=0.95,
        original_rrf_score=0.04,
        ranks=(2,),
    )

    historical_evidence = AnalysisEvidence(
        evidence_id="historical-001",
        text="Historical evidence.",
        source="UN Peacemaker",
        source_type=SourceType.UN_PEACEMAKER,
        perspective=Perspective.HISTORICAL,
        reranker_score=0.90,
        original_rrf_score=0.02,
        ranks=(3,),
    )

    context = EvidenceContext(
        query="India Pakistan conflict",
        evidence=(
            military_evidence,
            legal_evidence,
            historical_evidence,
        ),
        direct_evidence_ids=(
            "military-001",
            "legal-001",
            "historical-001",
        ),
        contextual_evidence_ids=(),
    )

    analyzer = EvidenceAnalyzer(llm)

    analyzer.analyze(context=context)

    calls = llm.generate_structured.call_args_list

    military_prompt = calls[0].kwargs["user_prompt"]
    legal_prompt = calls[1].kwargs["user_prompt"]
    historical_prompt = calls[2].kwargs["user_prompt"]

    assert "military-001" in military_prompt
    assert "legal-001" not in military_prompt
    assert "historical-001" not in military_prompt

    assert "legal-001" in legal_prompt
    assert "military-001" not in legal_prompt
    assert "historical-001" not in legal_prompt

    assert "historical-001" in historical_prompt
    assert "military-001" not in historical_prompt
    assert "legal-001" not in historical_prompt


def test_analyzer_preserves_direct_before_contextual_evidence() -> None:
    llm = make_llm()

    direct = AnalysisEvidence(
        evidence_id="direct-001",
        text="Direct evidence.",
        source="UCDP",
        source_type=SourceType.UCDP,
        perspective=Perspective.MILITARY,
        reranker_score=0.50,
        original_rrf_score=0.03,
        ranks=(1,),
    )

    contextual = AnalysisEvidence(
        evidence_id="context-001",
        text="Contextual military evidence.",
        source="UCDP",
        source_type=SourceType.UCDP,
        perspective=Perspective.MILITARY,
        reranker_score=0.99,
        original_rrf_score=0.04,
        ranks=(2,),
    )

    context = EvidenceContext(
        query="Military situation",
        evidence=(
            direct,
            contextual,
        ),
        direct_evidence_ids=("direct-001",),
        contextual_evidence_ids=("context-001",),
    )

    analyzer = EvidenceAnalyzer(llm)

    analyzer.analyze(context=context)

    prompt = llm.generate_structured.call_args_list[0].kwargs[
        "user_prompt"
    ]

    assert "direct-001" in prompt
    assert "context-001" in prompt

    assert prompt.index("direct-001") < prompt.index(
        "context-001"
    )