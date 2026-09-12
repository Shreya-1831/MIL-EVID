"""Build focused retrieval queries for each analytical perspective."""

from __future__ import annotations

from app.domain.enums import Perspective


class PerspectiveQueryBuilder:
    """Expand a user query with generic perspective-specific terms."""

    _TERMS = {
        Perspective.MILITARY: (
            "military forces armed conflict attacks operations "
            "weapons combat fighting casualties capabilities"
        ),
        Perspective.LEGAL: (
            "international humanitarian law IHL civilian protection "
            "distinction proportionality precautions targeting "
            "civilian objects responsibility"
        ),
        Perspective.HISTORICAL: (
            "historical background chronology conflict escalation "
            "ceasefire agreement settlement peace process diplomacy"
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