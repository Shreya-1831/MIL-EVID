"""Fixed top-5-per-source evidence selection after reranking."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.models.analysis import AnalysisEvidence


class PostRerankPerspectiveSelector:
    """Select the highest-ranked evidence from each available source.

    The cross-encoder remains responsible for relevance scoring and ranking.

    This experimental selector:
    1. groups reranked evidence by source;
    2. preserves the top five cross-encoder-ranked items from each source;
    3. restores the original global cross-encoder ordering;
    4. respects the final evidence budget.

    Unlike the production proportional selector, this experimental
    implementation intentionally uses a fixed per-source selection rule.
    """

    _PER_SOURCE_LIMIT = 5

    def select(
        self,
        *,
        query: str,
        evidence: Sequence[AnalysisEvidence],
        max_evidence: int,
    ) -> tuple[AnalysisEvidence, ...]:
        """Select up to five highest-ranked evidence items per source."""

        if max_evidence <= 0:
            return ()

        if not evidence:
            return ()

        selected: list[AnalysisEvidence] = []
        selected_ids: set[str] = set()
        source_counts: dict[str, int] = {}

        # Evidence is already ordered by cross-encoder score.
        # Therefore, the first five records encountered for each
        # source are that source's highest-ranked evidence.
        for item in evidence:
            source = item.source

            if not source:
                continue

            if source_counts.get(source, 0) >= self._PER_SOURCE_LIMIT:
                continue

            if item.evidence_id in selected_ids:
                continue

            selected.append(item)
            selected_ids.add(item.evidence_id)
            source_counts[source] = source_counts.get(source, 0) + 1

        # Restore the original cross-encoder ordering.
        evidence_order = {
            item.evidence_id: index
            for index, item in enumerate(evidence)
        }

        selected.sort(
            key=lambda item: evidence_order.get(
                item.evidence_id,
                len(evidence),
            )
        )

        return tuple(selected[:max_evidence])