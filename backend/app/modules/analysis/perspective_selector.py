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
    """Preserve perspective, entity and source diversity before reranking."""

    _PERSPECTIVE_KEYWORDS = {
        "military": {
            "military", "attack", "attacks", "armed", "force", "forces",
            "troops", "combat", "fighting", "clash", "clashes", "battle",
            "offensive", "defensive", "defense", "defence", "escalation",
            "operation", "operations", "weapon", "weapons", "artillery",
            "shelling", "airstrike", "airstrikes", "missile", "missiles",
            "casualties", "arms", "armaments", "military expenditure",
            "military spending",
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
            "historical", "history", "past", "previous", "prior",
            "background", "origins", "origin", "precedent", "precedents",
            "timeline", "evolution", "escalation", "conflict", "conflicts",
            "ceasefire", "peace", "agreement", "agreements", "settlement",
            "settlements",
        },
    }

    _SOURCE_PRIORITY = {
        "military": ("UCDP GED", "UCDP Dyadic", "SIPRI", "ACLED"),
        "legal": ("ICRC IHL Treaty", "ICRC Customary IHL"),
        "historical": (
            "UN Peacemaker", "UCDP GED", "UCDP Dyadic", "SIPRI", "ACLED",
        ),
    }

    _HISTORICAL_SOURCES = {
        "UN Peacemaker",
        "UCDP GED",
        "UCDP Dyadic",
        "SIPRI",
        "ACLED",
    }

    def __init__(
        self,
        *,
        preserve_per_perspective: int = 5,
        max_candidates: int = 30,
        min_sources_per_perspective: int = 2,
    ) -> None:
        if preserve_per_perspective <= 0:
            raise ValueError("preserve_per_perspective must be greater than 0")
        if max_candidates <= 0:
            raise ValueError("max_candidates must be greater than 0")
        if min_sources_per_perspective <= 0:
            raise ValueError("min_sources_per_perspective must be greater than 0")

        self._preserve_per_perspective = preserve_per_perspective
        self._max_candidates = max_candidates
        self._min_sources_per_perspective = min_sources_per_perspective

    @staticmethod
    def _query_entities(query: str) -> set[str]:
        text = query.lower()
        entities = set()

        for entity in (
            "russia", "ukraine", "china", "india", "pakistan",
            "israel", "palestine", "iran", "afghanistan",
            "united states", "usa", "uk", "france", "germany",
            "colombia",
        ):
            if re.search(rf"\b{re.escape(entity)}\b", text):
                entities.add(entity)

        return entities

    def select(
        self,
        *,
        query: str,
        candidates: Sequence[HybridSearchResult],
        evidence_by_id: Mapping[str, EvidenceDocument] | None = None,
    ) -> PerspectiveCandidateSelection:
        """Select candidates while enforcing perspective, entity and source diversity."""

        if not query or not query.strip() or not candidates:
            return PerspectiveCandidateSelection(tuple(), tuple())

        evidence_by_id = evidence_by_id or {}
        query_entities = self._query_entities(query)
        requested = self._detect_requested_perspectives(query)

        if not requested:
            return PerspectiveCandidateSelection(
                tuple(candidates[: self._max_candidates]),
                tuple(),
            )

        selected: list[HybridSearchResult] = []
        selected_ids: set[str] = set()

        # Reserve candidates for every requested perspective.
        for perspective in requested:
            pool = [
                c for c in candidates
                if self._candidate_matches_perspective(
                    candidate=c,
                    perspective=perspective,
                    evidence_by_id=evidence_by_id,
                    query_entities=query_entities,
                )
            ]

            if not pool:
                continue

            source_groups: dict[str, list[HybridSearchResult]] = {}
            for candidate in pool:
                source = self._get_source(
                    candidate=candidate,
                    evidence_by_id=evidence_by_id,
                )
                source_groups.setdefault(source, []).append(candidate)

            ordered_sources = self._order_sources(
                perspective=perspective,
                sources=list(source_groups),
            )

            added = 0

            # First preserve source diversity.
            for source in ordered_sources:
                for candidate in source_groups[source]:
                    if candidate.chunk_id in selected_ids:
                        continue

                    selected.append(candidate)
                    selected_ids.add(candidate.chunk_id)
                    added += 1
                    break

                if added >= min(
                    self._min_sources_per_perspective,
                    self._preserve_per_perspective,
                ):
                    break

                if len(selected) >= self._max_candidates:
                    break

            # Then fill the perspective quota.
            for candidate in pool:
                if len(selected) >= self._max_candidates:
                    break
                if candidate.chunk_id in selected_ids:
                    continue

                selected.append(candidate)
                selected_ids.add(candidate.chunk_id)
                added += 1

                if added >= self._preserve_per_perspective:
                    break

        # Fill remaining capacity using original hybrid ranking,
        # but only with candidates relevant to a requested perspective.
        for candidate in candidates:
            if len(selected) >= self._max_candidates:
                break
            if candidate.chunk_id in selected_ids:
                continue

            if any(
                self._candidate_matches_perspective(
                    candidate=candidate,
                    perspective=perspective,
                    evidence_by_id=evidence_by_id,
                    query_entities=query_entities,
                )
                for perspective in requested
            ):
                selected.append(candidate)
                selected_ids.add(candidate.chunk_id)

        return PerspectiveCandidateSelection(
            candidates=tuple(selected[: self._max_candidates]),
            requested_perspectives=tuple(requested),
        )

    def _get_source(
        self,
        *,
        candidate: HybridSearchResult,
        evidence_by_id: Mapping[str, EvidenceDocument],
    ) -> str:
        evidence = evidence_by_id.get(candidate.chunk_id)

        if evidence is not None and evidence.source:
            return evidence.source

        normalized = candidate.chunk_id.lower()

        if normalized.startswith("ucdp-ged-"):
            return "UCDP GED"
        if normalized.startswith("ucdp-dyadic-"):
            return "UCDP Dyadic"
        if normalized.startswith("sipri-"):
            return "SIPRI"
        if normalized.startswith("icrc::"):
            return "ICRC"
        if normalized.startswith("un_peacemaker::"):
            return "UN Peacemaker"
        if normalized.startswith("acled"):
            return "ACLED"

        return "unknown"

    def _order_sources(
        self,
        *,
        perspective: str,
        sources: Sequence[str],
    ) -> list[str]:
        source_set = set(sources)
        ordered = [
            source
            for source in self._SOURCE_PRIORITY.get(perspective, ())
            if source in source_set
        ]

        ordered.extend(source for source in sources if source not in ordered)
        return ordered

    def _detect_requested_perspectives(self, query: str) -> list[str]:
        normalized = self._normalize(query)
        return [
            perspective
            for perspective in ("military", "legal", "historical")
            if any(
                self._contains_keyword(normalized, keyword)
                for keyword in self._PERSPECTIVE_KEYWORDS[perspective]
            )
        ]

    def _candidate_matches_perspective(
        self,
        *,
        candidate: HybridSearchResult,
        perspective: str,
        evidence_by_id: Mapping[str, EvidenceDocument],
        query_entities: set[str] | None = None,
    ) -> bool:
        evidence = evidence_by_id.get(candidate.chunk_id)

        if evidence is not None:
            source = evidence.source
            text = " ".join(
                filter(None, (evidence.title, evidence.text, source))
            ).lower()

            # Historical evidence must be situation-specific.
            # Military perspective must allow conflict/event datasets directly.
            if perspective == "military":
                if source in {"UCDP GED", "UCDP Dyadic", "ACLED"}:
                    return True
            if perspective == "historical":
                if source not in self._HISTORICAL_SOURCES:
                    return False

                # Check both evidence text/metadata and the candidate ID.
                searchable = " ".join(
                    (
                        text,
                        candidate.chunk_id.lower(),
                        evidence.title.lower() if evidence.title else "",
                    )
                )

                if query_entities:
                    entity_match = any(
                        re.search(
                            rf"\b{re.escape(entity)}\b",
                            searchable,
                        )
                        for entity in query_entities
                    )

                    if not entity_match:
                        return False

                return True

            # Structured conflict/event datasets are military evidence.
            if source in {"UCDP GED", "UCDP Dyadic", "SIPRI", "ACLED"}:
                return perspective == "military"

            # Explicit perspective metadata wins.
            if evidence.perspective is not None:
                if evidence.perspective.value == perspective:
                    return True

            return any(
                self._contains_keyword(text, keyword)
                for keyword in self._PERSPECTIVE_KEYWORDS[perspective]
            )

        return self._candidate_id_matches_perspective(
            candidate.chunk_id,
            perspective,
        )

    def _candidate_id_matches_perspective(
        self,
        chunk_id: str,
        perspective: str,
    ) -> bool:
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

        return any(
            self._contains_keyword(normalized, keyword)
            for keyword in self._PERSPECTIVE_KEYWORDS[perspective]
        )

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.lower().split())

    @staticmethod
    def _contains_keyword(text: str, keyword: str) -> bool:
        keyword = " ".join(keyword.lower().split())

        if " " in keyword:
            return keyword in text

        return bool(re.search(rf"\b{re.escape(keyword)}\b", text))