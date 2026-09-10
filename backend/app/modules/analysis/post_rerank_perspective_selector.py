"""Proportion-aware and redundancy-aware evidence selection after reranking."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence

from app.domain.models.analysis import AnalysisEvidence


class PostRerankPerspectiveSelector:
    """Select a proportionally representative and diverse evidence set.

    The cross-encoder remains responsible for relevance scoring and ranking.

    This selector:
    1. determines the final evidence budget;
    2. calculates source proportions from available evidence;
    3. allocates the budget proportionally across sources;
    4. selects high-ranked evidence within each source;
    5. avoids highly redundant evidence;
    6. redistributes unused slots;
    7. restores cross-encoder ordering.

    No source-specific quotas are embedded here.
    """

    _REDUNDANCY_THRESHOLD = 0.80

    _STOPWORDS = {
        "a", "an", "and", "are", "as", "at", "be", "between",
        "by", "for", "from", "in", "into", "is", "it", "of",
        "on", "or", "that", "the", "their", "this", "to", "was",
        "were", "with",
    }

    def select(
        self,
        *,
        query: str,
        evidence: Sequence[AnalysisEvidence],
        max_evidence: int,
    ) -> tuple[AnalysisEvidence, ...]:
        """Select evidence proportionally across sources while limiting redundancy."""

        if max_evidence <= 0:
            return ()

        if not evidence:
            return ()

        if max_evidence >= len(evidence):
            return tuple(evidence)

        source_counts = Counter(
            item.source for item in evidence if item.source
        )

        if not source_counts:
            return tuple(evidence[:max_evidence])

        allocations = self._allocate_proportionally(
            source_counts=source_counts,
            total=max_evidence,
        )

        selected: list[AnalysisEvidence] = []
        selected_ids: set[str] = set()

        # Evidence is already ordered by cross-encoder score.
        # Therefore, candidates are examined from highest to lowest
        # relevance within each source.
        for source, allocation in allocations.items():
            if allocation <= 0:
                continue

            source_selected = [
                item for item in selected if item.source == source
            ]

            for item in evidence:
                if len(source_selected) >= allocation:
                    break

                if item.evidence_id in selected_ids:
                    continue

                if item.source != source:
                    continue

                if self._is_redundant(
                    candidate=item,
                    selected=source_selected,
                ):
                    continue

                selected.append(item)
                selected_ids.add(item.evidence_id)
                source_selected.append(item)

        # Redistribute unused slots caused by redundancy filtering,
        # rounding, or source shortages using global reranker order.
        for item in evidence:
            if len(selected) >= max_evidence:
                break

            if item.evidence_id in selected_ids:
                continue

            if self._is_redundant(
                candidate=item,
                selected=selected,
            ):
                continue

            selected.append(item)
            selected_ids.add(item.evidence_id)

        # Guarantee that the requested evidence budget can still be
        # filled if the redundancy check is unusually restrictive.
        for item in evidence:
            if len(selected) >= max_evidence:
                break

            if item.evidence_id in selected_ids:
                continue

            selected.append(item)
            selected_ids.add(item.evidence_id)

        # Restore original cross-encoder ordering.
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

    def _is_redundant(
        self,
        *,
        candidate: AnalysisEvidence,
        selected: Sequence[AnalysisEvidence],
    ) -> bool:
        """Return whether candidate is highly redundant with selected evidence."""

        if not selected:
            return False

        candidate_tokens = self._tokenize(candidate.text)

        if not candidate_tokens:
            return False

        for existing in selected:
            existing_tokens = self._tokenize(existing.text)

            if not existing_tokens:
                continue

            similarity = self._jaccard_similarity(
                candidate_tokens,
                existing_tokens,
            )

            if similarity >= self._REDUNDANCY_THRESHOLD:
                return True

        return False

    @classmethod
    def _tokenize(cls, text: str) -> set[str]:
        """Normalize evidence text into content-bearing tokens."""

        normalized = text.lower()
        tokens = re.findall(
            r"\b[a-z0-9][a-z0-9_-]*\b",
            normalized,
        )

        return {
            token for token in tokens
            if token not in cls._STOPWORDS and len(token) > 2
        }

    @staticmethod
    def _jaccard_similarity(
        left: set[str],
        right: set[str],
    ) -> float:
        """Calculate token-set Jaccard similarity."""

        if not left or not right:
            return 0.0

        intersection = len(left.intersection(right))
        union = len(left.union(right))

        if union == 0:
            return 0.0

        return intersection / union

    @staticmethod
    def _allocate_proportionally(
        *,
        source_counts: Counter[str],
        total: int,
    ) -> dict[str, int]:
        """Allocate evidence slots according to observed source proportions.

        Uses the largest-remainder method so integer allocations remain
        proportional while summing to the requested total.
        """

        population = sum(source_counts.values())

        if population <= 0 or total <= 0:
            return {}

        raw = {
            source: count / population * total
            for source, count in source_counts.items()
        }

        allocations = {
            source: min(int(value), source_counts[source])
            for source, value in raw.items()
        }

        remaining = total - sum(allocations.values())

        remainders = sorted(
            (
                (value - int(value), source)
                for source, value in raw.items()
                if allocations[source] < source_counts[source]
            ),
            reverse=True,
        )

        for _, source in remainders:
            if remaining <= 0:
                break

            if allocations[source] < source_counts[source]:
                allocations[source] += 1
                remaining -= 1

        return allocations