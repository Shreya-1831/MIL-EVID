"""
Reciprocal Rank Fusion (RRF) for combining ranked retrieval results.

RRF combines rankings from multiple retrieval systems without requiring
their raw scores to be on the same scale.

Formula:

    RRF(d) = sum(1 / (k + rank))

where:
    d    = document/chunk
    rank = 1-based rank in a retrieval result list
    k    = RRF constant
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


DEFAULT_RRF_K = 60


@dataclass(frozen=True)
class RRFSearchResult:
    """A single result produced by Reciprocal Rank Fusion."""

    chunk_id: str
    score: float
    ranks: tuple[int, ...]


def reciprocal_rank_fusion(
    result_lists: Sequence[Sequence],
    *,
    top_k: int = 10,
    k: int = DEFAULT_RRF_K,
) -> list[RRFSearchResult]:
    """Fuse multiple ranked result lists using RRF.

    Each input list must already be ordered from best to worst.

    Ranks are 1-based.

    Parameters
    ----------
    result_lists:
        Ranked retrieval result lists. Each result must expose a
        ``chunk_id`` attribute.

    top_k:
        Maximum number of fused results to return.

    k:
        RRF smoothing constant. The standard value is 60.

    Returns
    -------
    list[RRFSearchResult]
        Results ranked by fused RRF score, with deterministic
        chunk-ID tie-breaking.
    """

    if top_k <= 0:
        return []

    if k <= 0:
        raise ValueError("k must be greater than 0")

    scores: dict[str, float] = {}
    ranks: dict[str, list[int]] = {}

    for result_list in result_lists:
        seen_in_list: set[str] = set()

        for rank, result in enumerate(result_list, start=1):
            chunk_id = getattr(result, "chunk_id", None)

            if not isinstance(chunk_id, str) or not chunk_id:
                raise ValueError(
                    "Every retrieval result must contain a "
                    "non-empty string chunk_id."
                )

            # A retrieval list should not contain the same chunk twice.
            # Ignore accidental duplicates rather than double-counting.
            if chunk_id in seen_in_list:
                continue

            seen_in_list.add(chunk_id)

            scores[chunk_id] = (
                scores.get(chunk_id, 0.0)
                + 1.0 / (k + rank)
            )

            ranks.setdefault(chunk_id, []).append(rank)

    ranked = sorted(
        scores.items(),
        key=lambda pair: (-pair[1], pair[0]),
    )

    return [
        RRFSearchResult(
            chunk_id=chunk_id,
            score=float(score),
            ranks=tuple(ranks[chunk_id]),
        )
        for chunk_id, score in ranked[:top_k]
    ]