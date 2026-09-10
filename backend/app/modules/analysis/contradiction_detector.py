"""Evidence contradiction detection for MIL-EVID."""

from __future__ import annotations

import json

from app.domain.enums import ContradictionStatus, ContradictionType
from app.domain.models.analysis import (
    AnalysisEvidence,
    ContradictionResult,
)
from app.modules.analysis.llm_client import OllamaClient


class ContradictionDetector:
    """Detect contradictions between the most relevant evidence items."""

    # Maximum number of evidence comparisons sent to the LLM.
    MAX_COMPARISONS = 6

    def __init__(self, llm_client: OllamaClient) -> None:
        self._llm_client = llm_client

    def detect(
        self,
        *,
        evidence: tuple[AnalysisEvidence, ...],
    ) -> tuple[ContradictionResult, ...]:
        """Compare relevant evidence pairs and identify contradictions."""

        if len(evidence) < 2:
            return ()

        pairs: list[tuple[AnalysisEvidence, AnalysisEvidence]] = []

        # For small evidence sets, compare every pair.
        # This preserves complete contradiction checking when inexpensive.
        if len(evidence) <= 4:
            for index, evidence_a in enumerate(evidence):
                for evidence_b in evidence[index + 1:]:
                    pairs.append((evidence_a, evidence_b))

        else:
            # Evidence is already reranked, so prioritize nearby
            # high-ranked evidence.
            for index in range(len(evidence) - 1):
                if len(pairs) >= self.MAX_COMPARISONS:
                    break

                pairs.append(
                    (
                        evidence[index],
                        evidence[index + 1],
                    )
                )

            # Also compare the strongest evidence with later evidence.
            strongest = evidence[0]

            for item in evidence[2:]:
                if len(pairs) >= self.MAX_COMPARISONS:
                    break

                pair = (strongest, item)

                if pair not in pairs:
                    pairs.append(pair)

        results: list[ContradictionResult] = []

        for evidence_a, evidence_b in pairs:
            result = self._compare_pair(
                evidence_a=evidence_a,
                evidence_b=evidence_b,
            )

            if result is not None:
                results.append(result)

        return tuple(results)

    def _compare_pair(
        self,
        *,
        evidence_a: AnalysisEvidence,
        evidence_b: AnalysisEvidence,
    ) -> ContradictionResult | None:
        """Compare two evidence items using the LLM."""

        system_prompt = (
            "You are an evidence consistency analyst.\n\n"
            "Compare two supplied evidence items and determine whether "
            "they support each other, contradict each other, or cannot "
            "be meaningfully compared.\n\n"
            "Use ONLY the supplied evidence.\n"
            "Do not use general world knowledge.\n"
            "Do not assume missing facts.\n"
            "Do not treat differences in wording as contradictions.\n"
            "A contradiction requires the evidence to make incompatible "
            "claims about the same or directly comparable subject.\n"
            "A temporal difference is a contradiction only when the "
            "evidence describes incompatible states for the same "
            "time-sensitive fact.\n\n"
            "Return ONLY valid JSON with these fields:\n"
            "status: one of ENTAILMENT, CONTRADICTION, NEUTRAL\n"
            "contradiction_type: one of FACTUAL, TEMPORAL, UNCERTAIN, NONE\n"
            "score: number between 0 and 1\n"
            "explanation: short explanation"
        )

        user_prompt = (
            "EVIDENCE A\n"
            f"ID: {evidence_a.evidence_id}\n"
            f"Source: {evidence_a.source}\n"
            f"Title: {evidence_a.title}\n"
            f"Date: {evidence_a.date}\n"
            f"Text: {evidence_a.text}\n\n"
            "EVIDENCE B\n"
            f"ID: {evidence_b.evidence_id}\n"
            f"Source: {evidence_b.source}\n"
            f"Title: {evidence_b.title}\n"
            f"Date: {evidence_b.date}\n"
            f"Text: {evidence_b.text}\n\n"
            "Determine the relationship between Evidence A and Evidence B."
        )

        raw_response = self._llm_client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        parsed = self._parse_response(raw_response)

        if parsed is None:
            return ContradictionResult(
                evidence_a_id=evidence_a.evidence_id,
                evidence_b_id=evidence_b.evidence_id,
                status=ContradictionStatus.NEUTRAL,
                contradiction_type=ContradictionType.UNCERTAIN,
                score=0.0,
                explanation=(
                    "Unable to reliably determine the relationship."
                ),
            )

        return ContradictionResult(
            evidence_a_id=evidence_a.evidence_id,
            evidence_b_id=evidence_b.evidence_id,
            status=parsed["status"],
            contradiction_type=parsed["contradiction_type"],
            score=parsed["score"],
            explanation=parsed["explanation"],
        )

    @staticmethod
    def _parse_response(
        response: str,
    ) -> dict | None:
        """Parse and validate the LLM contradiction response."""

        try:
            data = json.loads(response)
        except (TypeError, json.JSONDecodeError):
            return None

        if not isinstance(data, dict):
            return None

        try:
            status = ContradictionStatus(
                str(data["status"]).strip().lower()
            )

            contradiction_type = ContradictionType(
                str(data["contradiction_type"]).strip().lower()
            )

            score = float(data["score"])
            explanation = str(data["explanation"])

        except (KeyError, TypeError, ValueError):
            return None

        if not 0.0 <= score <= 1.0:
            return None

        return {
            "status": status,
            "contradiction_type": contradiction_type,
            "score": score,
            "explanation": explanation,
        }