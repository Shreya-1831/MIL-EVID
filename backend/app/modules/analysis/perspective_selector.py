"""Perspective-aware candidate selection before cross-encoder reranking."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Sequence

from app.domain.models.evidence import EvidenceDocument
from app.modules.retrieval.hybrid_retriever import HybridSearchResult


@dataclass(frozen=True)
class PerspectiveCandidateSelection:
    """Selected hybrid candidates preserved for cross-encoder reranking."""

    candidates: tuple[HybridSearchResult, ...]
    requested_perspectives: tuple[str, ...]


class PerspectiveAwareCandidateSelector:
    """Preserve relevant multi-perspective candidates before reranking."""

    _PERSPECTIVE_KEYWORDS = {
        "military": {
            "military", "attack", "attacks", "armed", "force", "forces",
            "troops", "combat", "fighting", "clash", "clashes", "battle",
            "offensive", "defensive", "defense", "defence", "escalation",
            "operation", "operations", "weapon", "weapons", "artillery",
            "shelling", "airstrike", "airstrikes", "missile", "missiles",
            "casualties",
        },
        "legal": {
            "legal", "law", "lawful", "unlawful", "legality", "ihl",
            "international", "humanitarian", "civilian", "civilians",
            "protection", "protected", "distinction", "proportionality",
            "precautions", "targeting", "target", "targets", "war crime",
            "war crimes", "treaty", "treaties", "convention", "conventions",
            "rights",
        },
        "historical": {
            "historical", "history", "past", "previous", "prior", "background",
            "origins", "precedent", "precedents", "timeline", "evolution",
            "escalation", "conflict", "conflicts", "ceasefire", "peace",
            "agreement", "agreements", "settlement", "settlements",
        },
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
        evidence_by_id: Mapping[str, EvidenceDocument] | None = None,
    ) -> PerspectiveCandidateSelection:
        """Select relevant candidates for the requested perspectives."""
        if not query or not query.strip() or not candidates:
            return PerspectiveCandidateSelection(
                candidates=tuple(),
                requested_perspectives=tuple(),
            )

        requested = self._detect_requested_perspectives(query)

        if not requested:
            return PerspectiveCandidateSelection(
                candidates=tuple(candidates[: self._max_candidates]),
                requested_perspectives=tuple(),
            )

        evidence_by_id = evidence_by_id or {}

        selected: list[HybridSearchResult] = []
        selected_ids: set[str] = set()

        for perspective in requested:
            perspective_candidates = [
                candidate
                for candidate in candidates
                if candidate.chunk_id not in selected_ids
                and self._candidate_matches_perspective(
                    candidate=candidate,
                    perspective=perspective,
                    evidence_by_id=evidence_by_id,
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
        evidence_by_id: Mapping[str, EvidenceDocument],
    ) -> bool:
        """Determine whether evidence supports the requested perspective."""
        evidence = evidence_by_id.get(candidate.chunk_id)

        if evidence is not None:
            if evidence.source in {"UCDP GED", "UCDP Dyadic"}:
                return perspective == "military"

            if evidence.perspective is not None:
                return evidence.perspective.value == perspective

            text = " ".join(
                filter(
                    None,
                    (
                        evidence.title,
                        evidence.text,
                        evidence.source,
                    ),
                )
            ).lower()

            keywords = self._PERSPECTIVE_KEYWORDS[perspective]

            if any(
                self._contains_keyword(text, keyword)
                for keyword in keywords
            ):
                return True

        return self._candidate_id_matches_perspective(
            candidate.chunk_id,
            perspective,
        )

    def _candidate_id_matches_perspective(
        self,
        chunk_id: str,
        perspective: str,
    ) -> bool:
        """Legacy fallback for candidates without resolvable metadata."""

        normalized = chunk_id.lower()

        if normalized.startswith("icrc::"):
            return perspective == "legal"

        if normalized.startswith("un_peacemaker::"):
            return perspective == "historical"

        if normalized.startswith(("ucdp-ged-", "ucdp-dyadic-")):
            return perspective in {"historical", "military"}

        if normalized.startswith("sipri-"):
            return perspective in {"historical", "military"}

        if normalized.startswith("acled"):
            return perspective in {"historical", "military"}

        keywords = self._PERSPECTIVE_KEYWORDS[perspective]

        return any(
            self._contains_keyword(normalized, keyword)
            for keyword in keywords
        )

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.lower().split())

    @staticmethod
    def _contains_keyword(text: str, keyword: str) -> bool:
        normalized_keyword = " ".join(keyword.lower().split())

        if " " in normalized_keyword:
            return normalized_keyword in text

        return bool(
            re.search(
                rf"\b{re.escape(normalized_keyword)}\b",
                text,
            )
        )