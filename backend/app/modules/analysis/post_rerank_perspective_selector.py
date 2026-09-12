"""Diverse evidence selection after cross-encoder reranking."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.models.analysis import AnalysisEvidence


class PostRerankPerspectiveSelector:
    """Select reranked evidence with source diversity.

    Evidence is first grouped by source while preserving cross-encoder
    ordering within each source. Items are then selected round-robin
    across sources so that one source cannot consume the entire budget.
    """

    _PER_SOURCE_LIMIT = 5

    def select(
        self,
        *,
        query: str,
        evidence: Sequence[AnalysisEvidence],
        max_evidence: int,
    ) -> tuple[AnalysisEvidence, ...]:
        """Select diverse evidence while preserving reranker ordering."""

        if max_evidence <= 0 or not evidence:
            return ()

        source_groups: dict[str, list[AnalysisEvidence]] = {}

        for item in evidence:
            source = item.source
            if not source:
                continue

            group = source_groups.setdefault(source, [])

            if len(group) < self._PER_SOURCE_LIMIT:
                group.append(item)

        if not source_groups:
            return ()

        selected: list[AnalysisEvidence] = []
        selected_ids: set[str] = set()

        # Take one highly-ranked item from each source, then repeat.
        # This prevents one source from consuming the entire budget.
        for round_index in range(self._PER_SOURCE_LIMIT):
            for group in source_groups.values():
                if round_index >= len(group):
                    continue

                item = group[round_index]

                if item.evidence_id in selected_ids:
                    continue

                selected.append(item)
                selected_ids.add(item.evidence_id)

                if len(selected) >= max_evidence:
                    return tuple(selected)

        return tuple(selected)