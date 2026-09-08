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
    """Separates query-relevant evidence from potentially contextual evidence."""

    def filter(
        self,
        *,
        query: str,
        evidence: tuple[AnalysisEvidence, ...],
    ) -> EvidenceGuardResult:
        query_entities = self._extract_entities(query)

        direct: list[AnalysisEvidence] = []
        contextual: list[AnalysisEvidence] = []

        for item in evidence:
            evidence_entities = self._extract_entities(
                f"{item.title} {item.text}"
            )

            if self._is_consistent(query_entities, evidence_entities):
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
    def _is_consistent(
        query_entities: set[str],
        evidence_entities: set[str],
    ) -> bool:
        if not query_entities:
            return True

        if not evidence_entities:
            return False

        # For multi-country queries, require all identified
        # query countries to appear in the evidence.
        if len(query_entities) >= 2:
            return query_entities.issubset(evidence_entities)

        return bool(query_entities.intersection(evidence_entities))