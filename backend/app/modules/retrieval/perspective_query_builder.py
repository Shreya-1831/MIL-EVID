"""Build focused retrieval queries for each analytical perspective."""

from __future__ import annotations

from app.domain.enums import Perspective


class PerspectiveQueryBuilder:
    """Build perspective- and source-aware retrieval queries."""

    _TERMS = {
        Perspective.MILITARY: (
            "military forces armed conflict attacks operations "
            "weapons combat fighting casualties capabilities "
            "arms transfers weapons transfers military equipment "
            "defense procurement suppliers recipients deliveries "
            "UCDP SIPRI"
        ),
        Perspective.LEGAL: (
            "international humanitarian law IHL civilian protection "
            "distinction proportionality precautions targeting "
            "civilian objects responsibility lawful unlawful "
            "war crimes ICRC"
        ),
        Perspective.HISTORICAL: (
            "historical background chronology conflict escalation "
            "ceasefire agreement settlement peace process diplomacy "
            "Minsk agreement Minsk II negotiation political settlement "
            "eastern Ukraine Russia Ukraine conflict timeline "
            "UN Peacemaker"
        ),
    }

    def build(
        self,
        query: str,
        perspectives: tuple[Perspective, ...],
    ) -> dict[Perspective, str]:
        """Build one focused query per perspective."""

        normalized_query = " ".join(query.strip().split())

        return {
            perspective: (
                f"{normalized_query} "
                f"{self._TERMS.get(perspective, '')}"
            ).strip()
            for perspective in perspectives
        }