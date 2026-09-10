from unittest.mock import Mock

from app.domain.enums import ContradictionStatus, ContradictionType
from app.domain.models.analysis import AnalysisEvidence
from app.modules.analysis.contradiction_detector import (
    ContradictionDetector,
)


def make_evidence(
    evidence_id: str,
    text: str,
) -> AnalysisEvidence:
    return AnalysisEvidence(
        evidence_id=evidence_id,
        text=text,
        source="test",
        source_type="ucdp",
        perspective="military",
        title="Test Evidence",
        date=None,
        url=None,
        document_id="doc-1",
        chunk_index=0,
        reranker_score=1.0,
        original_rrf_score=1.0,
        ranks=(),
    )


def test_detects_contradiction():
    llm = Mock()
    llm.generate_structured.return_value = {
        "results": [
            {
                "pair_index": 1,
                "status": "CONTRADICTION",
                "contradiction_type": "FACTUAL",
                "score": 0.95,
                "explanation": "The evidence gives incompatible facts.",
            }
        ]
    }

    detector = ContradictionDetector(llm)

    evidence = (
        make_evidence("a", "The forces entered the area."),
        make_evidence("b", "The forces did not enter the area."),
    )

    result = detector.detect(evidence=evidence)

    assert len(result) == 1
    assert result[0].status == ContradictionStatus.CONTRADICTION
    assert result[0].contradiction_type == ContradictionType.FACTUAL
    assert result[0].score == 0.95


def test_detects_entailment():
    llm = Mock()
    llm.generate_structured.return_value = {
        "results": [
            {
                "pair_index": 1,
                "status": "ENTAILMENT",
                "contradiction_type": "NONE",
                "score": 0.90,
                "explanation": (
                    "Both evidence items support the same fact."
                ),
            }
        ]
    }

    detector = ContradictionDetector(llm)

    evidence = (
        make_evidence(
            "a",
            "Shelling occurred near the border.",
        ),
        make_evidence(
            "b",
            "Artillery fire was reported near the border.",
        ),
    )

    result = detector.detect(evidence=evidence)

    assert len(result) == 1
    assert result[0].status == ContradictionStatus.ENTAILMENT
    assert result[0].contradiction_type == ContradictionType.NONE


def test_detects_neutral():
    llm = Mock()
    llm.generate_structured.return_value = {
        "results": [
            {
                "pair_index": 1,
                "status": "NEUTRAL",
                "contradiction_type": "NONE",
                "score": 0.20,
                "explanation": (
                    "The evidence concerns different facts."
                ),
            }
        ]
    }

    detector = ContradictionDetector(llm)

    evidence = (
        make_evidence(
            "a",
            "A ceasefire was announced.",
        ),
        make_evidence(
            "b",
            "Three civilians were displaced.",
        ),
    )

    result = detector.detect(evidence=evidence)

    assert len(result) == 1
    assert result[0].status == ContradictionStatus.NEUTRAL


def test_invalid_llm_response_is_uncertain():
    llm = Mock()
    llm.generate_structured.side_effect = RuntimeError(
        "Invalid structured response"
    )

    detector = ContradictionDetector(llm)

    evidence = (
        make_evidence("a", "Evidence A."),
        make_evidence("b", "Evidence B."),
    )

    result = detector.detect(evidence=evidence)

    assert len(result) == 1
    assert result[0].status == ContradictionStatus.NEUTRAL
    assert result[0].contradiction_type == ContradictionType.UNCERTAIN
    assert result[0].score == 0.0


def test_empty_evidence_returns_no_results():
    llm = Mock()
    detector = ContradictionDetector(llm)

    result = detector.detect(evidence=())

    assert result == ()
    llm.generate_structured.assert_not_called()


def test_three_evidence_items_create_three_pairs():
    llm = Mock()
    llm.generate_structured.return_value = {
        "results": [
            {
                "pair_index": 1,
                "status": "NEUTRAL",
                "contradiction_type": "NONE",
                "score": 0.1,
                "explanation": "No contradiction.",
            },
            {
                "pair_index": 2,
                "status": "NEUTRAL",
                "contradiction_type": "NONE",
                "score": 0.1,
                "explanation": "No contradiction.",
            },
            {
                "pair_index": 3,
                "status": "NEUTRAL",
                "contradiction_type": "NONE",
                "score": 0.1,
                "explanation": "No contradiction.",
            },
        ]
    }

    detector = ContradictionDetector(llm)

    evidence = (
        make_evidence("a", "Evidence A."),
        make_evidence("b", "Evidence B."),
        make_evidence("c", "Evidence C."),
    )

    result = detector.detect(evidence=evidence)

    assert len(result) == 3
    assert llm.generate_structured.call_count == 1