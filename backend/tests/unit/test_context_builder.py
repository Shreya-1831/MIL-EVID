"""Unit tests for the Phase 10 evidence context builder."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from app.domain.enums import Perspective, SourceType
from app.domain.models.analysis import (
    AnalysisEvidence,
    EvidenceContext,
)
from app.domain.models.evidence import EvidenceDocument
from app.modules.analysis.context_builder import EvidenceContextBuilder
from app.modules.retrieval.reranker import RerankedSearchResult
from app.repositories.chunk_file_store import replace_chunks


def _make_chunk(
    *,
    chunk_id: str = "chunk-1",
    text: str = "Evidence text.",
    source: str = "UCDP",
    perspective: Perspective | None = Perspective.MILITARY,
) -> EvidenceDocument:
    """Create a valid evidence chunk for tests."""

    return EvidenceDocument(
        id=chunk_id,
        text=text,
        source=source,
        source_type=SourceType.UCDP,
        perspective=perspective,
        title="Test Evidence",
        date=datetime(2026, 1, 15),
        url="https://example.com/evidence",
        document_id="document-1",
        chunk_index=0,
        metadata={"test": True},
    )


def _make_result(
    *,
    chunk_id: str = "chunk-1",
    score: float = 0.9,
    original_rrf_score: float = 0.03,
    ranks: tuple[int, ...] = (1, 2),
) -> RerankedSearchResult:
    """Create a reranked result for tests."""

    return RerankedSearchResult(
        chunk_id=chunk_id,
        score=score,
        original_rrf_score=original_rrf_score,
        ranks=ranks,
    )


def test_build_empty_results_returns_empty_context(tmp_path: Path) -> None:
    """Empty reranked results should produce an empty context."""

    builder = EvidenceContextBuilder(
        chunk_store_dir=tmp_path,
    )

    result = builder.build(
        query="military conflict",
        reranked_results=[],
    )

    assert isinstance(result, EvidenceContext)
    assert result.query == "military conflict"
    assert result.evidence == ()


def test_build_blank_query_returns_empty_context(tmp_path: Path) -> None:
    """Blank queries should not produce analysis evidence."""

    builder = EvidenceContextBuilder(
        chunk_store_dir=tmp_path,
    )

    result = builder.build(
        query="   ",
        reranked_results=[
            _make_result(),
        ],
    )

    assert result.query == "   "
    assert result.evidence == ()


def test_build_resolves_chunk_from_store(tmp_path: Path) -> None:
    """A reranked chunk ID should resolve to its stored evidence."""

    replace_chunks(
        [
            _make_chunk(
                chunk_id="chunk-1",
                text="Civilian displacement increased.",
            )
        ],
        chunk_store_dir=tmp_path,
    )

    builder = EvidenceContextBuilder(
        chunk_store_dir=tmp_path,
    )

    result = builder.build(
        query="civilian displacement",
        reranked_results=[
            _make_result(
                chunk_id="chunk-1",
                score=0.91,
                original_rrf_score=0.02,
                ranks=(2, 4),
            )
        ],
    )

    assert len(result.evidence) == 1

    evidence = result.evidence[0]

    assert isinstance(evidence, AnalysisEvidence)
    assert evidence.evidence_id == "chunk-1"
    assert evidence.text == "Civilian displacement increased."
    assert evidence.source == "UCDP"
    assert evidence.source_type == SourceType.UCDP
    assert evidence.perspective == Perspective.MILITARY
    assert evidence.title == "Test Evidence"
    assert evidence.document_id == "document-1"
    assert evidence.chunk_index == 0

    assert evidence.reranker_score == pytest.approx(0.91)
    assert evidence.original_rrf_score == pytest.approx(0.02)
    assert evidence.ranks == (2, 4)


def test_build_preserves_reranked_order(tmp_path: Path) -> None:
    """Evidence should remain in the reranker's ordering."""

    replace_chunks(
        [
            _make_chunk(
                chunk_id="chunk-1",
                text="First evidence.",
            ),
            _make_chunk(
                chunk_id="chunk-2",
                text="Second evidence.",
            ),
        ],
        chunk_store_dir=tmp_path,
    )

    builder = EvidenceContextBuilder(
        chunk_store_dir=tmp_path,
    )

    result = builder.build(
        query="military conflict",
        reranked_results=[
            _make_result(
                chunk_id="chunk-2",
                score=0.95,
            ),
            _make_result(
                chunk_id="chunk-1",
                score=0.80,
            ),
        ],
    )

    assert [item.evidence_id for item in result.evidence] == [
        "chunk-2",
        "chunk-1",
    ]

    assert [item.reranker_score for item in result.evidence] == [
        pytest.approx(0.95),
        pytest.approx(0.80),
    ]


def test_build_preserves_optional_metadata(tmp_path: Path) -> None:
    """Optional evidence metadata should survive context construction."""

    chunk = EvidenceDocument(
        id="chunk-legal",
        text="Legal evidence text.",
        source="ICRC",
        source_type=SourceType.ICRC_IHL,
        perspective=Perspective.LEGAL,
        title=None,
        date=None,
        url=None,
        document_id=None,
        chunk_index=None,
    )

    replace_chunks(
        [chunk],
        chunk_store_dir=tmp_path,
    )

    builder = EvidenceContextBuilder(
        chunk_store_dir=tmp_path,
    )

    result = builder.build(
        query="applicable IHL",
        reranked_results=[
            _make_result(
                chunk_id="chunk-legal",
            )
        ],
    )

    evidence = result.evidence[0]

    assert evidence.source_type == SourceType.ICRC_IHL
    assert evidence.perspective == Perspective.LEGAL
    assert evidence.title is None
    assert evidence.date is None
    assert evidence.url is None
    assert evidence.document_id is None
    assert evidence.chunk_index is None


def test_build_omits_missing_chunks(tmp_path: Path) -> None:
    """Missing chunk IDs should never create fabricated evidence."""

    replace_chunks(
        [
            _make_chunk(
                chunk_id="existing",
                text="Existing evidence.",
            )
        ],
        chunk_store_dir=tmp_path,
    )

    builder = EvidenceContextBuilder(
        chunk_store_dir=tmp_path,
    )

    result = builder.build(
        query="military conflict",
        reranked_results=[
            _make_result(
                chunk_id="missing",
                score=0.99,
            ),
            _make_result(
                chunk_id="existing",
                score=0.80,
            ),
        ],
    )

    assert [item.evidence_id for item in result.evidence] == [
        "existing",
    ]


def test_context_is_immutable(tmp_path: Path) -> None:
    """Analysis context models should remain immutable."""

    replace_chunks(
        [
            _make_chunk(),
        ],
        chunk_store_dir=tmp_path,
    )

    builder = EvidenceContextBuilder(
        chunk_store_dir=tmp_path,
    )

    result = builder.build(
        query="test query",
        reranked_results=[
            _make_result(),
        ],
    )

    with pytest.raises(Exception):
        result.query = "changed"  # type: ignore[misc]

    with pytest.raises(Exception):
        result.evidence = ()  # type: ignore[misc]