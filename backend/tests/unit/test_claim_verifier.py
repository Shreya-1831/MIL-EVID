from unittest.mock import Mock

from app.domain.enums import ClaimVerificationStatus
from app.domain.models.analysis import AnalysisEvidence
from app.modules.analysis.claim_verifier import ClaimVerifier


def make_evidence(
    evidence_id: str,
    text: str,
) -> AnalysisEvidence:
    return AnalysisEvidence(
        evidence_id=evidence_id,
        text=text,
        source="UCDP",
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


def test_supported_claim() -> None:
    llm = Mock()

    llm.generate_structured.return_value = {
        "supporting_evidence_ids": ["e1"],
        "support_score": 0.95,
        "status": "SUPPORTED",
    }

    verifier = ClaimVerifier(llm)

    evidence = (
        make_evidence(
            "e1",
            "Artillery exchanges occurred near the border.",
        ),
    )

    result = verifier.verify(
        claims=("Artillery exchanges occurred near the border.",),
        evidence=evidence,
    )

    assert len(result) == 1
    assert result[0].claim == (
        "Artillery exchanges occurred near the border."
    )
    assert result[0].supporting_evidence_ids == ("e1",)
    assert result[0].support_score == 0.95
    assert result[0].status == ClaimVerificationStatus.SUPPORTED
    assert result[0].verified is True


def test_partially_supported_claim() -> None:
    llm = Mock()

    llm.generate_structured.return_value = {
        "supporting_evidence_ids": ["e1"],
        "support_score": 0.55,
        "status": "PARTIALLY_SUPPORTED",
    }

    verifier = ClaimVerifier(llm)

    evidence = (
        make_evidence(
            "e1",
            "Artillery exchanges were reported near a populated area.",
        ),
    )

    result = verifier.verify(
        claims=(
            "Artillery exchanges caused widespread civilian casualties.",
        ),
        evidence=evidence,
    )

    assert len(result) == 1
    assert result[0].status == (
        ClaimVerificationStatus.PARTIALLY_SUPPORTED
    )
    assert result[0].support_score == 0.55
    assert result[0].supporting_evidence_ids == ("e1",)
    assert result[0].verified is False


def test_unsupported_claim() -> None:
    llm = Mock()

    llm.generate_structured.return_value = {
        "supporting_evidence_ids": [],
        "support_score": 0.05,
        "status": "UNSUPPORTED",
    }

    verifier = ClaimVerifier(llm)

    evidence = (
        make_evidence(
            "e1",
            "A ceasefire agreement was discussed.",
        ),
    )

    result = verifier.verify(
        claims=("The forces used missile strikes.",),
        evidence=evidence,
    )

    assert len(result) == 1
    assert result[0].supporting_evidence_ids == ()
    assert result[0].status == ClaimVerificationStatus.UNSUPPORTED
    assert result[0].verified is False


def test_invalid_llm_response_is_unsupported() -> None:
    llm = Mock()

    # Simulate structured-output failure.
    llm.generate_structured.side_effect = RuntimeError(
        "Invalid structured response"
    )

    verifier = ClaimVerifier(llm)

    evidence = (
        make_evidence(
            "e1",
            "Some evidence.",
        ),
    )

    result = verifier.verify(
        claims=("Some claim.",),
        evidence=evidence,
    )

    assert len(result) == 1
    assert result[0].status == ClaimVerificationStatus.UNSUPPORTED
    assert result[0].support_score == 0.0
    assert result[0].verified is False


def test_empty_claim_is_unsupported() -> None:
    llm = Mock()

    verifier = ClaimVerifier(llm)

    evidence = (
        make_evidence(
            "e1",
            "Some evidence.",
        ),
    )

    result = verifier.verify(
        claims=("   ",),
        evidence=evidence,
    )

    assert len(result) == 1
    assert result[0].status == ClaimVerificationStatus.UNSUPPORTED
    assert result[0].support_score == 0.0
    assert result[0].supporting_evidence_ids == ()
    assert result[0].verified is False

    llm.generate_structured.assert_not_called()


def test_empty_evidence_produces_unsupported_claim() -> None:
    llm = Mock()

    llm.generate_structured.return_value = {
        "supporting_evidence_ids": [],
        "support_score": 0.0,
        "status": "UNSUPPORTED",
    }

    verifier = ClaimVerifier(llm)

    result = verifier.verify(
        claims=("Some claim.",),
        evidence=(),
    )

    assert len(result) == 1
    assert result[0].supporting_evidence_ids == ()
    assert result[0].status == ClaimVerificationStatus.UNSUPPORTED
    assert result[0].verified is False


def test_unknown_evidence_ids_are_removed() -> None:
    llm = Mock()

    llm.generate_structured.return_value = {
        "supporting_evidence_ids": [
            "e1",
            "fake-id",
        ],
        "support_score": 0.9,
        "status": "SUPPORTED",
    }

    verifier = ClaimVerifier(llm)

    evidence = (
        make_evidence(
            "e1",
            "The claim is supported.",
        ),
    )

    result = verifier.verify(
        claims=("The claim is supported.",),
        evidence=evidence,
    )

    assert result[0].supporting_evidence_ids == ("e1",)
    assert result[0].verified is True