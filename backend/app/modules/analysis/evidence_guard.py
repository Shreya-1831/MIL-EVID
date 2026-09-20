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
    """Keeps only evidence relevant to the requested situation."""

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
                evidence_source=item.source,
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
            "united kingdom",
            "uk",
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
        topics = {
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
        normalized = normalized.replace(
            "international humanitarian law",
            "international_humanitarian_law",
        )

        return {
            topic
            for topic in topics
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
        evidence_source: str | None = None,
    ) -> bool:

        # --------------------------------------------------------------
        # MILITARY
        # Only situation/event evidence should pass.
        # UCDP GED / UCDP Dyadic / ACLED are military evidence sources.
        # --------------------------------------------------------------
        if perspective == "military":

            military_sources = {
                "ucdp ged",
                "ucdp dyadic",
                "acled",
            }

            source = (evidence_source or "").lower()

            is_military_source = any(
                name in source
                for name in military_sources
            )

            if not is_military_source:
                return False

            if query_entities:
                if not evidence_entities:
                    return False

                if len(query_entities) >= 2:
                    if not query_entities.issubset(evidence_entities):
                        return False
                elif not query_entities.intersection(evidence_entities):
                    return False

            if query_topics:
                if not evidence_topics:
                    return False

                if not query_topics.intersection(evidence_topics):
                    return False

            return True

        # --------------------------------------------------------------
        # LEGAL
        # --------------------------------------------------------------
        if perspective == "legal":

            if query_entities and evidence_entities:
                if len(query_entities) >= 2:
                    if not query_entities.intersection(evidence_entities):
                        return False

            return True

        # --------------------------------------------------------------
        # HISTORICAL
        # --------------------------------------------------------------
        if perspective == "historical":
            return bool(evidence_entities or evidence_topics)

        # --------------------------------------------------------------
        # DEFAULT
        # --------------------------------------------------------------
        if query_entities:
            if not evidence_entities:
                return False

            if len(query_entities) >= 2:
                if not query_entities.issubset(evidence_entities):
                    return False
            elif not query_entities.intersection(evidence_entities):
                return False

        if query_topics:
            if not evidence_topics:
                return False

            if not query_topics.intersection(evidence_topics):
                return False

        return True