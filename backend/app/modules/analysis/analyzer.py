"""Evidence-grounded multi-perspective analysis."""

from __future__ import annotations

from app.domain.enums import Perspective
from app.domain.models.analysis import (
    EvidenceContext,
    PerspectiveAnalysisResult,
)
from app.modules.analysis.llm_client import OllamaClient


class EvidenceAnalyzer:
    """Generate evidence-grounded analysis for each perspective."""

    def __init__(self, llm_client: OllamaClient) -> None:
        self._llm_client = llm_client

    def analyze(
        self,
        *,
        context: EvidenceContext,
    ) -> tuple[
        PerspectiveAnalysisResult,
        PerspectiveAnalysisResult,
        PerspectiveAnalysisResult,
    ]:
        """Generate military, legal, and historical analyses."""

        military = self._analyze_perspective(
            context=context,
            perspective=Perspective.MILITARY,
        )

        legal = self._analyze_perspective(
            context=context,
            perspective=Perspective.LEGAL,
        )

        historical = self._analyze_perspective(
            context=context,
            perspective=Perspective.HISTORICAL,
        )

        return military, legal, historical

    def _analyze_perspective(
        self,
        *,
        context: EvidenceContext,
        perspective: Perspective,
    ) -> PerspectiveAnalysisResult:
        """Generate analysis for one perspective."""

        system_prompt = self._build_system_prompt(perspective)
        user_prompt = self._build_user_prompt(context)

        analysis_text = self._llm_client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        evidence_ids = tuple(
            evidence.evidence_id
            for evidence in context.evidence
        )

        return PerspectiveAnalysisResult(
            perspective=perspective,
            analysis_text=analysis_text,
            evidence_ids=evidence_ids,
            citations=(),
        )

    @staticmethod
    def _build_system_prompt(
        perspective: Perspective,
    ) -> str:
        """Build a perspective-specific system prompt."""

        perspective_instructions = {
            Perspective.MILITARY: (
                "Analyze the military and operational aspects of "
                "the situation, including actors, events, conflict "
                "dynamics, and relevant military developments."
            ),
            Perspective.LEGAL: (
                "Analyze the international humanitarian law and "
                "legal aspects of the situation. Focus only on "
                "legal conclusions supported by the evidence."
            ),
            Perspective.HISTORICAL: (
                "Analyze the historical context, background, "
                "precedents, and developments relevant to the "
                "situation."
            ),
        }

        return (
            "You are an evidence-grounded military situation "
            "analyst.\n\n"
            f"{perspective_instructions[perspective]}\n\n"
            "Use only the supplied evidence. Do not invent facts, "
            "events, dates, actors, or legal conclusions.\n"
            "If the evidence is insufficient, explicitly state "
            "that it is insufficient.\n"
            "Distinguish facts from interpretation.\n"
            "Keep the analysis concise and factual."
        )

    @staticmethod
    def _build_user_prompt(
        context: EvidenceContext,
    ) -> str:
        """Format the query and retrieved evidence."""

        evidence_sections: list[str] = []

        for index, evidence in enumerate(
            context.evidence,
            start=1,
        ):
            evidence_sections.append(
                "\n".join(
                    [
                        f"[Evidence {index}]",
                        f"ID: {evidence.evidence_id}",
                        f"Source: {evidence.source}",
                        f"Text: {evidence.text}",
                    ]
                )
            )

        evidence_text = "\n\n".join(evidence_sections)

        return (
            f"Query:\n{context.query}\n\n"
            "Retrieved evidence:\n"
            f"{evidence_text}\n\n"
            "Provide an evidence-grounded analysis of the query."
        )