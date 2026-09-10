"""Perspective-aware candidate selection before cross-encoder reranking."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from app.modules.retrieval.hybrid_retriever import HybridSearchResult


@dataclass(frozen=True)
class PerspectiveCandidateSelection:
    """Selected hybrid candidates preserved for cross-encoder reranking."""

    candidates: tuple[HybridSearchResult, ...]
    requested_perspectives: tuple[str, ...]


class PerspectiveAwareCandidateSelector:
    """Preserve relevant multi-perspective candidates before reranking.

    The selector does not replace the cross-encoder. It only prevents
    potentially useful perspective-specific evidence from disappearing
    before cross-encoder scoring.

    Selection is query-aware and does not enforce a fixed number of
    military/legal/historical documents.
    """

    _PERSPECTIVE_KEYWORDS = {
        "military": {
            "military",
            "attack",
            "attacks",
            "armed",
            "force",
            "forces",
            "troops",
            "combat",
            "fighting",
            "clash",
            "clashes",
            "battle",
            "offensive",
            "defensive",
            "defense",
            "defence",
            "escalation",
            "operation",
            "operations",
            "weapon",
            "weapons",
            "artillery",
            "shelling",
            "airstrike",
            "airstrikes",
            "missile",
            "missiles",
            "casualties",
        },
        "legal": {
            "legal",
            "law",
            "lawful",
            "unlawful",
            "legality",
            "ihl",
            "international",
            "humanitarian",
            "humanitarian",
            "civilian",
            "civilians",
            "protection",
            "protected",
            "distinction",
            "proportionality",
            "precautions",
            "targeting",
            "target",
            "targets",
            "war crime",
            "war crimes",
            "treaty",
            "treaties",
            "convention",
            "conventions",
            "rights",
        },
        "historical": {
            "historical",
            "history",
            "past",
            "previous",
            "prior",
            "background",
            "origins",
            "precedent",
            "precedents",
            "timeline",
            "evolution",
            "escalation",
            "conflict",
            "conflicts",
            "ceasefire",
            "peace",
            "agreement",
            "agreements",
            "settlement",
            "settlements",
        },
    }

    _SOURCE_PERSPECTIVES = {
        "ICRC Customary IHL": {"legal"},
        "ICRC IHL Treaty": {"legal"},
        "UN Peacemaker": {"historical"},
        "UCDP Dyadic": {"historical", "military"},
        "UCDP GED": {"historical", "military"},
        "SIPRI Arms Transfers Database": {"military", "historical"},
        "ACLED": {"military", "historical"},
    }

    def __init__(
        self,
        *,
        preserve_per_perspective: int = 5,
        max_candidates: int = 30,
    ) -> None:
        if preserve_per_perspective <= 0:
            raise ValueError(
                "preserve_per_perspective must be greater than 0"
            )

        if max_candidates <= 0:
            raise ValueError(
                "max_candidates must be greater than 0"
            )

        self._preserve_per_perspective = preserve_per_perspective
        self._max_candidates = max_candidates

    def select(
        self,
        *,
        query: str,
        candidates: Sequence[HybridSearchResult],
    ) -> PerspectiveCandidateSelection:
        """Select a perspective-aware candidate pool.

        Candidates remain ordered primarily by their original RRF ranking.
        Perspective-specific candidates are preserved before filling the
        remaining slots with the strongest global candidates.
        """

        if not query or not query.strip():
            return PerspectiveCandidateSelection(
                candidates=tuple(),
                requested_perspectives=tuple(),
            )

        if not candidates:
            return PerspectiveCandidateSelection(
                candidates=tuple(),
                requested_perspectives=tuple(),
            )

        requested = self._detect_requested_perspectives(query)

        # If the query does not explicitly indicate a perspective,
        # preserve the original hybrid candidate ordering.
        if not requested:
            return PerspectiveCandidateSelection(
                candidates=tuple(candidates[: self._max_candidates]),
                requested_perspectives=tuple(),
            )

        selected: list[HybridSearchResult] = []
        selected_ids: set[str] = set()

        # Preserve strong candidates relevant to each requested perspective.
        #
        # We use a relevance threshold based on query/perspective keyword
        # overlap rather than forcing a fixed number of documents.
        for perspective in requested:
            perspective_candidates = [
                candidate
                for candidate in candidates
                if candidate.chunk_id not in selected_ids
                and self._candidate_matches_perspective(
                    candidate=candidate,
                    perspective=perspective,
                )
            ]

            for candidate in perspective_candidates[
                : self._preserve_per_perspective
            ]:
                selected.append(candidate)
                selected_ids.add(candidate.chunk_id)

                if len(selected) >= self._max_candidates:
                    break

            if len(selected) >= self._max_candidates:
                break

        # Fill remaining slots with the strongest original RRF candidates.
        for candidate in candidates:
            if len(selected) >= self._max_candidates:
                break

            if candidate.chunk_id in selected_ids:
                continue

            selected.append(candidate)
            selected_ids.add(candidate.chunk_id)

        # Restore original hybrid ordering. The selector should preserve
        # candidates, not invent a new ranking before the cross-encoder.
        candidate_order = {
            candidate.chunk_id: index
            for index, candidate in enumerate(candidates)
        }

        selected.sort(
            key=lambda candidate: candidate_order.get(
                candidate.chunk_id,
                len(candidates),
            )
        )

        return PerspectiveCandidateSelection(
            candidates=tuple(selected),
            requested_perspectives=tuple(requested),
        )

    def _detect_requested_perspectives(
        self,
        query: str,
    ) -> list[str]:
        """Detect perspectives explicitly or implicitly requested by query."""

        normalized = self._normalize(query)

        detected: list[str] = []

        for perspective in (
            "military",
            "legal",
            "historical",
        ):
            keywords = self._PERSPECTIVE_KEYWORDS[perspective]

            if any(
                self._contains_keyword(normalized, keyword)
                for keyword in keywords
            ):
                detected.append(perspective)

        return detected

    def _candidate_matches_perspective(
        self,
        *,
        candidate: HybridSearchResult,
        perspective: str,
    ) -> bool:
        """Determine whether a candidate is associated with a perspective."""

        # HybridSearchResult intentionally contains retrieval metadata,
        # not source text. Therefore use the chunk ID/source naming convention
        # available in the retrieval candidate when possible.
        candidate_id = candidate.chunk_id.lower()

        source_perspectives = self._infer_source_perspectives(
            candidate_id
        )

        if perspective in source_perspectives:
            return True

        # Fallback based on chunk ID vocabulary.
        keywords = self._PERSPECTIVE_KEYWORDS[perspective]

        return any(
            self._contains_keyword(candidate_id, keyword)
            for keyword in keywords
        )

    def _infer_source_perspectives(
        self,
        chunk_id: str,
    ) -> set[str]:
        """Infer likely perspectives from the chunk ID/source prefix."""

        normalized = chunk_id.lower()

        if normalized.startswith("icrc::"):
            if "treat" in normalized or "treaty" in normalized:
                return {"legal"}

            return {"legal"}

        if normalized.startswith("un_peacemaker::"):
            return {"historical"}

        if normalized.startswith("ucdp-ged-"):
            return {"historical", "military"}

        if normalized.startswith("ucdp-dyadic-"):
            return {"historical", "military"}

        if normalized.startswith("sipri"):
            return {"military", "historical"}

        if normalized.startswith("acled"):
            return {"military", "historical"}

        return set()

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for keyword matching."""

        return " ".join(text.lower().split())

    @staticmethod
    def _contains_keyword(
        text: str,
        keyword: str,
    ) -> bool:
        """Return whether keyword occurs as a complete lexical unit."""

        normalized_keyword = " ".join(keyword.lower().split())

        if " " in normalized_keyword:
            return normalized_keyword in text

        return bool(
            re.search(
                rf"\b{re.escape(normalized_keyword)}\b",
                text,
            )
        )