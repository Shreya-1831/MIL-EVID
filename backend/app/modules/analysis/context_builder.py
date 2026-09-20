"""Build structured analysis context from reranked evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from app.domain.models.analysis import (
    AnalysisEvidence,
    EvidenceContext,
)
from app.domain.models.evidence import EvidenceDocument
from app.repositories.chunk_file_store import get_chunks_by_id
from app.modules.retrieval.reranker import (
    RerankedEvidence,
    RerankedSearchResult,
)


class EvidenceContextBuilder:
    """Resolve reranked evidence into LLM-ready evidence context."""

    def __init__(self, *, chunk_store_dir: Path) -> None:
        self._chunk_store_dir = chunk_store_dir

    @property
    def chunk_store_dir(self) -> Path:
        """Return the configured chunk-store directory."""
        return self._chunk_store_dir

    def build(
        self,
        *,
        query: str,
        reranked_results: Sequence[RerankedSearchResult],
    ) -> EvidenceContext:
        """Build structured evidence context from static reranked results."""

        if not query or not query.strip():
            return EvidenceContext(
                query=query,
                evidence=(),
            )

        if not reranked_results:
            return EvidenceContext(
                query=query,
                evidence=(),
            )

        chunk_ids = [
            result.chunk_id
            for result in reranked_results
        ]

        chunks = get_chunks_by_id(
            chunk_ids,
            chunk_store_dir=self._chunk_store_dir,
        )

        evidence: list[AnalysisEvidence] = []

        for result in reranked_results:
            chunk = chunks.get(result.chunk_id)

            # Never fabricate evidence when a reranked chunk cannot
            # be resolved from the source-of-truth chunk store.
            if chunk is None:
                continue

            evidence.append(
                self._to_analysis_evidence(
                    result=result,
                    chunk=chunk,
                )
            )

        return EvidenceContext(
            query=query,
            evidence=tuple(evidence),
        )

    def build_dynamic(
        self,
        *,
        query: str,
        reranked_evidence: Sequence[RerankedEvidence],
    ) -> EvidenceContext:
        """Build evidence context from dynamically retrieved documents."""

        if not query or not query.strip():
            return EvidenceContext(
                query=query,
                evidence=(),
            )

        if not reranked_evidence:
            return EvidenceContext(
                query=query,
                evidence=(),
            )

        evidence = tuple(
            self._to_dynamic_analysis_evidence(
                result=result,
            )
            for result in reranked_evidence
        )

        return EvidenceContext(
            query=query,
            evidence=evidence,
        )

    @staticmethod
    def _to_analysis_evidence(
        *,
        result: RerankedSearchResult,
        chunk: EvidenceDocument,
    ) -> AnalysisEvidence:
        """Convert static retrieval data into analysis evidence."""

        return AnalysisEvidence(
            evidence_id=chunk.id,
            text=chunk.text,
            source=chunk.source,
            source_type=chunk.source_type,
            perspective=chunk.perspective,
            title=chunk.title,
            date=chunk.date,
            url=chunk.url,
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            reranker_score=result.score,
            original_rrf_score=result.original_rrf_score,
            ranks=result.ranks,
        )

    @staticmethod
    def _to_dynamic_analysis_evidence(
        *,
        result: RerankedEvidence,
    ) -> AnalysisEvidence:
        """Convert dynamic evidence into analysis evidence."""

        evidence = result.evidence

        return AnalysisEvidence(
            evidence_id=evidence.id,
            text=evidence.text,
            source=evidence.source,
            source_type=evidence.source_type,
            perspective=evidence.perspective,
            title=evidence.title,
            date=evidence.date,
            url=evidence.url,
            document_id=evidence.document_id,
            chunk_index=evidence.chunk_index,
            reranker_score=result.score,
            original_rrf_score=0.0,
            ranks=(),
        )