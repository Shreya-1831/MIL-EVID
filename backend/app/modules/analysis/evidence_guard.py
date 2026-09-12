"""Evidence consistency guard for analysis context."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.models.analysis import AnalysisEvidence


@dataclass(frozen=True)
class EvidenceGuardResult:
    direct_evidence: tuple[AnalysisEvidence, ...]
    contextual_evidence: tuple[AnalysisEvidence, ...]


class EvidenceConsistencyGuard:
    """Separates situation-relevant evidence from contextual evidence."""

    def filter(
        self,
        *,
        query: str,
        evidence: tuple[AnalysisEvidence, ...],
        perspective: str | None = None,
    ) -> EvidenceGuardResult:
        query_entities = self._extract_entities(query)
        query_topics = self._extract_topics(query)

        direct: list[AnalysisEvidence] = []
        contextual: list[AnalysisEvidence] = []

        for item in evidence:
            evidence_text = f"{item.title} {item.text}"

            evidence_entities = self._extract_entities(evidence_text)
            evidence_topics = self._extract_topics(evidence_text)

            if self._is_directly_relevant(
                query_entities=query_entities,
                evidence_entities=evidence_entities,
                query_topics=query_topics,
                evidence_topics=evidence_topics,
                perspective=perspective,
            ):
                direct.append(item)
            else:
                contextual.append(item)

        return EvidenceGuardResult(
            direct_evidence=tuple(direct),
            contextual_evidence=tuple(contextual),
        )

    @staticmethod
    def _extract_entities(text: str) -> set[str]:
        """Extract common country/actor names relevant to military queries."""

        countries = {
            "india",
            "pakistan",
            "china",
            "russia",
            "ukraine",
            "israel",
            "palestine",
            "iran",
            "iraq",
            "syria",
            "afghanistan",
            "turkey",
            "united states",
            "usa",
            "north korea",
            "south korea",
        }

        normalized = text.lower()

        return {
            country
            for country in countries
            if re.search(rf"\b{re.escape(country)}\b", normalized)
        }

    @staticmethod
    def _extract_topics(text: str) -> set[str]:
        """Extract broad situation-level topics from military queries."""

        topic_keywords = {
            "artillery",
            "shelling",
            "airstrike",
            "airstrikes",
            "missile",
            "missiles",
            "attack",
            "attacks",
            "escalation",
            "conflict",
            "clash",
            "clashes",
            "fighting",
            "fire",
            "ceasefire",
            "border",
            "civilian",
            "civilians",
            "civilian_infrastructure",
            "infrastructure",
            "populated",
            "population",
            "casualties",
            "displacement",
            "military",
            "troops",
            "forces",
            "defensive",
            "defense",
            "defence",
            "humanitarian",
            "international_humanitarian_law",
            "ihl",
            "war",
        }

        normalized = text.lower()

        # Normalize common multi-word concepts.
        normalized = normalized.replace(
            "civilian infrastructure",
            "civilian_infrastructure",
        )
        normalized = normalized.replace(
            "international humanitarian law",
            "international_humanitarian_law",
        )

        return {
            topic
            for topic in topic_keywords
            if re.search(rf"\b{re.escape(topic)}\b", normalized)
        }

    @staticmethod
    def _is_directly_relevant(
        *,
        query_entities: set[str],
        evidence_entities: set[str],
        query_topics: set[str],
        evidence_topics: set[str],
        perspective: str | None = None,
    ) -> bool:
        """
        Determine whether evidence is sufficiently aligned with the query.

        Direct evidence requires:
        1. Country/entity consistency.
        2. At least one meaningful topic overlap.

        For multi-country queries, all identified query countries must
        appear in the evidence.
        """

        # If the query contains identifiable countries, the evidence
        # must contain the same country set.
        # Legal evidence can be generally applicable IHL doctrine.
        # It does not need to mention the specific countries in the query.
        if perspective != "legal" and query_entities:
            if not evidence_entities:
                return False

            if len(query_entities) >= 2:
                if not query_entities.issubset(evidence_entities):
                    return False
            elif not query_entities.intersection(evidence_entities):
                return False

        # Country consistency alone is not enough.
        # Require meaningful situation/topic overlap.
        if query_topics:
            if not evidence_topics:
                return False

            topic_overlap = query_topics.intersection(evidence_topics)

            if not topic_overlap:
                return False

        return True