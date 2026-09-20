"""Build focused retrieval queries for each analytical perspective."""

from __future__ import annotations

from app.domain.enums import Perspective


class PerspectiveQueryBuilder:
    """Build query-specific retrieval queries for each perspective."""

    _TERMS = {
        Perspective.MILITARY: (
            "military forces armed conflict attacks operations "
            "weapons combat fighting casualties capabilities "
            "arms transfers weapons transfers military equipment "
            "defense procurement suppliers recipients deliveries "
            "conflict intensity military actors"
        ),
        Perspective.LEGAL: (
            "international humanitarian law IHL civilian protection "
            "distinction proportionality precautions targeting "
            "civilian objects military objectives responsibility "
            "lawful unlawful attacks war crimes "
            "protection of civilians ICRC"
        ),
    }

    _HISTORICAL_TERMS = (
        "historical context chronology timeline origins "
        "developments escalation turning points "
        "ceasefire agreements peace negotiations "
        "peace settlement diplomatic efforts "
        "prior agreements historical events conflict trajectory"
    )

    _HISTORICAL_FOCUS_QUERIES = (
        "historical context chronology origins developments",
        "ceasefire agreements peace negotiations settlements",
        "historical events turning points conflict trajectory",
    )

    def build(
        self,
        query: str,
        perspectives: tuple[Perspective, ...],
    ) -> dict[Perspective, str | tuple[str, ...]]:
        """Build query-specific focused retrieval queries."""

        normalized_query = " ".join(
            query.strip().split()
        )

        result: dict[
            Perspective,
            str | tuple[str, ...],
        ] = {}

        for perspective in perspectives:

            if perspective == Perspective.HISTORICAL:
                result[perspective] = tuple(
                    f"{normalized_query} {focus}"
                    for focus in self._HISTORICAL_FOCUS_QUERIES
                )

                continue

            perspective_terms = self._TERMS.get(
                perspective,
                "",
            )

            result[perspective] = (
                f"{normalized_query} {perspective_terms}"
            ).strip()

        return result