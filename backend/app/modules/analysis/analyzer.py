"""Evidence-grounded multi-perspective analysis."""

from __future__ import annotations

import json
import logging

from app.domain.enums import Perspective
from app.domain.models.analysis import (
    AnalysisEvidence,
    Citation,
    EvidenceContext,
    PerspectiveAnalysisResult,
)
from app.modules.analysis.llm_client import OllamaClient
from app.modules.analysis.query_specificity_check import QuerySpecificityChecker

logger = logging.getLogger("mil_evid")


class EvidenceAnalyzer:
    """Generate evidence-grounded analysis for each perspective."""

    ANALYSIS_SCHEMA = {
        "type": "object",
        "properties": {
            "analysis": {
                "type": "string",
            },
            "claims": {
                "type": "array",
                "items": {
                    "type": "string",
                },
            },
        },
        "required": ["analysis", "claims"],
        "additionalProperties": False,
    }

    # Source-to-perspective relevance mapping.
    #
    # This does NOT create quotas or change retrieval.
    # It only tells the analyzer which perspectives a source can
    # meaningfully support when constructing the LLM evidence view.
    _SOURCE_PERSPECTIVES = {
        "ICRC Customary IHL": {
            Perspective.LEGAL,
        },
        "ICRC IHL Treaty": {
            Perspective.LEGAL,
        },
        "UN Peacemaker": {
            Perspective.HISTORICAL,
        },
        "UCDP Dyadic": {
            Perspective.MILITARY,
            Perspective.HISTORICAL,
        },
        "UCDP GED": {
            Perspective.MILITARY,
            Perspective.HISTORICAL,
        },
        "SIPRI Arms Transfers Database": {
            Perspective.MILITARY,
            Perspective.HISTORICAL,
        },
        "ACLED": {
            Perspective.MILITARY,
            Perspective.HISTORICAL,
        },
    }

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

        military_context = self._build_perspective_context(
            context=context,
            perspective=Perspective.MILITARY,
        )

        legal_context = self._build_perspective_context(
            context=context,
            perspective=Perspective.LEGAL,
        )

        historical_context = self._build_perspective_context(
            context=context,
            perspective=Perspective.HISTORICAL,
        )

        military = self._analyze_perspective(
            context=military_context,
            perspective=Perspective.MILITARY,
        )

        legal = self._analyze_perspective(
            context=legal_context,
            perspective=Perspective.LEGAL,
        )

        historical = self._analyze_perspective(
            context=historical_context,
            perspective=Perspective.HISTORICAL,
        )

        return military, legal, historical

    @classmethod
    def _build_perspective_context(
        cls,
        *,
        context: EvidenceContext,
        perspective: Perspective,
    ) -> EvidenceContext:
        """
        Build a perspective-specific evidence view.

        Evidence is not re-retrieved or re-scored here. The existing
        selected evidence is preserved, but evidence relevant to the
        requested perspective is placed first within the
        direct/contextual groups.

        This allows each LLM analysis to focus on the most relevant
        perspective without introducing source-specific quotas.
        """

        if not context.evidence:
            return context

        direct_ids = set(context.direct_evidence_ids)

        direct_evidence: list[AnalysisEvidence] = []
        contextual_evidence: list[AnalysisEvidence] = []

        for evidence in context.evidence:
            if evidence.evidence_id in direct_ids:
                direct_evidence.append(evidence)
            else:
                contextual_evidence.append(evidence)

        def matches_perspective(
            evidence: AnalysisEvidence,
        ) -> bool:
            """
            Determine whether evidence is relevant to the perspective.

            Explicit evidence perspective takes priority. The source
            mapping is then used to recognize sources that legitimately
            support multiple perspectives, such as UCDP.
            """

            if evidence.perspective == perspective:
                return True

            return perspective in cls._SOURCE_PERSPECTIVES.get(
                evidence.source,
                set(),
            )

        def evidence_priority(
            evidence: AnalysisEvidence,
        ) -> tuple[int, float]:
            """
            Put perspective-relevant evidence first, then use the
            existing reranker score to preserve relevance ordering.
            """

            return (
                0 if matches_perspective(evidence) else 1,
                -evidence.reranker_score,
            )

        direct_evidence.sort(key=evidence_priority)
        contextual_evidence.sort(key=evidence_priority)

        # Preserve perspective-relevant evidence first while keeping
        # the existing direct/contextual evidence distinction.
        #
        # No source quotas are introduced here.
        # No retrieval scores are changed.
        # No new evidence is retrieved.
        #
        # The perspective-specific view is intentionally focused so
        # that a small local LLM does not become dominated by a large
        # amount of repetitive evidence from an unrelated perspective.

        perspective_direct = [
            evidence
            for evidence in direct_evidence
            if matches_perspective(evidence)
        ]

        remaining_direct = [
            evidence
            for evidence in direct_evidence
            if not matches_perspective(evidence)
        ]

        perspective_contextual = [
            evidence
            for evidence in contextual_evidence
            if matches_perspective(evidence)
        ]

        remaining_contextual = [
            evidence
            for evidence in contextual_evidence
            if not matches_perspective(evidence)
        ]

        # ordered_evidence = tuple(
        #     perspective_direct
        #     + remaining_direct
        #     + perspective_contextual
        #     + remaining_contextual
        # )

        ordered_evidence = tuple(
            perspective_direct
            + perspective_contextual
        )

        logger.warning(
            "\n========== PERSPECTIVE EVIDENCE DEBUG ==========\n"
            "Perspective: %s\n"
            "%s"
            "===============================================\n",
            perspective.value,
            "\n".join(
                (
                    f"{index}. "
                    f"source={evidence.source!r}, "
                    f"perspective={evidence.perspective!r}, "
                    f"reranker={evidence.reranker_score:.4f}, "
                    f"id={evidence.evidence_id}"
                )
                for index, evidence in enumerate(ordered_evidence, start=1)
            ),
        )

        return EvidenceContext(
            query=context.query,
            evidence=ordered_evidence,
            direct_evidence_ids=context.direct_evidence_ids,
            contextual_evidence_ids=context.contextual_evidence_ids,
        )

    @staticmethod
    def _validate_analysis_specificity(
        *,
        query: str,
        analysis_text: str,
    ) -> None:
        """Log a warning when generated analysis appears too generic."""

        is_specific, reason = QuerySpecificityChecker.check_analysis(
            query=query,
            analysis=analysis_text,
        )

        if not is_specific:
            logger.warning(
                "Analysis specificity check failed: %s",
                reason,
            )

    def _analyze_perspective(
        self,
        *,
        context: EvidenceContext,
        perspective: Perspective,
    ) -> PerspectiveAnalysisResult:
        """Generate analysis and explicitly identified claims."""

        system_prompt = self._build_system_prompt(
            perspective
        )

        user_prompt = self._build_user_prompt(
            context=context,
            perspective=perspective,
        )

        structured_response = self._llm_client.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=self.ANALYSIS_SCHEMA,
        )

        analysis_text, claims = self._parse_structured_response(
            structured_response
        )

        # Diagnostic validation only.
        # It does not alter the generated analysis.
        self._validate_analysis_specificity(
            query=context.query,
            analysis_text=analysis_text,
        )

        evidence_ids = tuple(
            evidence.evidence_id
            for evidence in context.evidence
        )

        citations = tuple(
            Citation(
                evidence_id=evidence.evidence_id,
                source=evidence.source,
                title=evidence.title,
                url=evidence.url,
            )
            for evidence in context.evidence
        )

        return PerspectiveAnalysisResult(
            perspective=perspective,
            analysis_text=analysis_text,
            claims=claims,
            evidence_ids=evidence_ids,
            citations=citations,
        )

    @staticmethod
    def _parse_structured_response(
        response: dict,
    ) -> tuple[str, tuple[str, ...]]:
        """Parse the validated structured analysis response."""

        analysis = response.get("analysis", "")
        raw_claims = response.get("claims", [])

        if not isinstance(analysis, str):
            raise RuntimeError(
                "Structured analysis response contains an invalid "
                "'analysis' field."
            )

        if not isinstance(raw_claims, list):
            raise RuntimeError(
                "Structured analysis response contains an invalid "
                "'claims' field."
            )

        claims = tuple(
            str(claim).strip()
            for claim in raw_claims
            if str(claim).strip()
        )

        return analysis.strip(), claims

    @staticmethod
    def _parse_analysis_response(
        response: str,
    ) -> tuple[str, tuple[str, ...]]:
        """Parse legacy structured or unstructured LLM responses."""

        if not response.strip():
            return "", ()

        try:
            data = json.loads(response)

            if isinstance(data, dict):
                analysis = data.get("analysis", "")
                raw_claims = data.get("claims", [])

                if (
                    isinstance(analysis, str)
                    and isinstance(raw_claims, list)
                ):
                    claims = tuple(
                        str(claim).strip()
                        for claim in raw_claims
                        if str(claim).strip()
                    )

                    return analysis.strip(), claims

        except (TypeError, json.JSONDecodeError):
            pass

        return response.strip(), ()

    @staticmethod
    def _build_system_prompt(
        perspective: Perspective,
    ) -> str:
        """Build a perspective-specific system prompt."""

        perspective_instructions = {
            Perspective.MILITARY: (
                "Analyze only the military and operational aspects "
                "supported by the PRIMARY EVIDENCE. Focus on actors, "
                "documented attacks and conflict events, military "
                "developments, conflict dynamics, operational "
                "implications, and escalation risks explicitly "
                "supported by that evidence. When the query identifies "
                "specific countries or actors, keep the military "
                "analysis explicitly grounded in those entities. "
                "Do not infer specific military actions, capabilities, "
                "intentions, deployments, or events unless supported "
                "by the supplied evidence. Do not turn the military "
                "analysis into a generic discussion of international "
                "humanitarian law."
            ),
            Perspective.LEGAL: (
                "Analyze the international humanitarian law and legal "
                "aspects supported by the PRIMARY EVIDENCE. Focus only "
                "on legal conclusions explicitly supported by that "
                "evidence, including distinction, civilian protection, "
                "proportionality, precautions, and the legal assessment "
                "of attacks where supported. When the query identifies "
                "specific countries, actors, or events, explicitly "
                "distinguish the queried situation from general legal "
                "principles. Do not treat agreements, legal provisions, "
                "or rules from a different country pair or conflict "
                "as applicable to the queried situation unless the "
                "PRIMARY EVIDENCE explicitly establishes that "
                "applicability."
            ),
            Perspective.HISTORICAL: (
                "Analyze only the historical context, background, "
                "precedents, chronology, and developments contained "
                "in the PRIMARY EVIDENCE. Prioritize documented "
                "historical events, conflict patterns, and developments "
                "involving the countries or actors identified in the "
                "query. Do not replace the requested historical "
                "assessment with a generic international humanitarian "
                "law explanation. Historical evidence from another "
                "country pair or conflict may be discussed only as "
                "contextual comparison. Do not introduce historical "
                "events from general knowledge. Do not claim that a "
                "historical agreement, mechanism, principle, or "
                "precedent applies to the queried situation unless "
                "the PRIMARY EVIDENCE explicitly establishes that "
                "connection."
            ),
        }

        return (
            "You are an evidence-grounded military situation analyst.\n\n"
            f"{perspective_instructions[perspective]}\n\n"

            "QUERY-SPECIFIC ANALYSIS REQUIREMENT:\n"
            "Answer the user's actual query rather than merely "
            "summarizing the supplied evidence.\n"
            "If the query names specific countries, actors, locations, "
            "or events, explicitly refer to those entities in the "
            "analysis when they are relevant and supported by the "
            "evidence.\n"
            "Do not replace named entities with generic phrases such "
            "as 'the parties', 'the states', 'the conflict', or "
            "'the region' when doing so would make the analysis less "
            "specific.\n"
            "Keep the analysis focused on the requested perspective.\n\n"

            "CRITICAL GROUNDING REQUIREMENTS:\n"
            "1. Use ONLY the supplied evidence as factual support.\n"
            "2. PRIMARY EVIDENCE is the only evidence that may support "
            "situation-specific factual, legal, military, or historical "
            "claims.\n"
            "3. CONTEXTUAL EVIDENCE may ONLY be used for general "
            "background or clearly labeled comparison.\n"
            "4. Never use CONTEXTUAL EVIDENCE to establish that an "
            "event, agreement, legal provision, obligation, actor, "
            "military action, date, or outcome applies to the query.\n"
            "5. Never transfer facts or conclusions between different "
            "country pairs, conflicts, borders, locations, or "
            "historical events.\n"
            "6. Do not use general world knowledge to fill gaps in the "
            "supplied evidence.\n"
            "7. Do not introduce historical events, agreements, legal "
            "articles, military facts, actors, dates, or recommendations "
            "that are not supported by the supplied evidence.\n"
            "8. If the query describes a hypothetical or assumed "
            "situation, do not present those assumptions as independently "
            "verified facts unless the evidence confirms them.\n"
            "9. If PRIMARY EVIDENCE is insufficient, explicitly state "
            "that the evidence is insufficient.\n"
            "10. Distinguish evidence-supported facts from interpretation "
            "and clearly identify contextual comparisons.\n"
            "11. Do not present a contextual comparison as a legal rule, "
            "military fact, historical fact, or established "
            "applicability.\n"
            "12. Keep the analysis concise, factual, and "
            "evidence-grounded.\n\n"

            "CLAIM IDENTIFICATION:\n"
            "Generate ONLY 2 to 4 atomic factual claims.\n\n"

            "Each claim must describe ONE specific fact from ONE "
            "DIRECT EVIDENCE record.\n\n"

            "CLAIM RULES:\n"
            "1. Every claim must be directly verifiable from a single "
            "DIRECT EVIDENCE record whenever possible.\n"
            "2. Copy factual values EXACTLY from the evidence.\n"
            "3. Copy dates EXACTLY as written in the evidence.\n"
            "4. Never convert a date into a time such as 00:00.0.\n"
            "5. Copy locations, actor names, fatality counts, targets, "
            "and event descriptions exactly from the evidence.\n"
            "6. Do not calculate numbers.\n"
            "7. Do not aggregate numbers from multiple events.\n"
            "8. Do not combine facts from different evidence records "
            "into one claim.\n"
            "9. Do not generalize one event into a statement about the "
            "entire conflict.\n"
            "10. Do not infer facts that are not explicitly stated.\n"
            "11. Do not use general world knowledge.\n\n"

            "GOOD CLAIMS:\n"
            "- The event occurred in Kharkiv, Ukraine.\n"
            "- The event resulted in 3 reported fatalities.\n"
            "- The event involved the Government of Russia "
            "(Soviet Union).\n"
            "- The event involved the Government of Ukraine.\n"
            "- The event targeted residential buildings.\n\n"

            "BAD CLAIMS:\n"
            "- The Russia-Ukraine conflict has escalated significantly.\n"
            "- Fatalities ranged from 1 to 8.\n"
            "- The attacks demonstrate increasing risks to civilians.\n"
            "- The conflict caused significant damage across Ukraine.\n"
            "- The attacks were intended to target civilians.\n"
            "- Further investigation is needed.\n\n"

            "Do NOT create:\n"
            "- broad conflict summaries\n"
            "- recommendations\n"
            "- opinions\n"
            "- interpretations\n"
            "- legal conclusions\n"
            "- causal claims\n"
            "- motivation or intention claims\n"
            "- claims requiring calculations\n"
            "- claims requiring aggregation across events\n"
            "- generic statements about civilian protection\n\n"

            "If the DIRECT EVIDENCE does not contain enough concrete "
            "facts for 2 claims, generate fewer claims rather than "
            "inventing or generalizing information.\n\n"

            "Every claim must be independently checkable by locating "
            "the same fact directly in a DIRECT EVIDENCE record.\n"
            "Do not create claims from general world knowledge.\n\n"

            "Return ONLY valid JSON in this exact structure:\n"
            "{\n"
            '  "analysis": "concise evidence-grounded analysis",\n'
            '  "claims": ["claim 1", "claim 2"]\n'
            "}"
        )

    @classmethod
    def _build_user_prompt(
        cls,
        *,
        context: EvidenceContext,
        perspective: Perspective,
    ) -> str:
        """Format the query and separate direct/contextual evidence."""

        direct_ids = set(context.direct_evidence_ids)
        contextual_ids = set(context.contextual_evidence_ids)

        direct_sections: list[str] = []
        contextual_sections: list[str] = []

        direct_index = 1
        contextual_index = 1

        def perspective_relevance(
            evidence: AnalysisEvidence,
        ) -> str:
            """
            Label evidence according to its relevance to the current
            analysis perspective.
            """

            if evidence.perspective == perspective:
                return "PRIMARY"

            if perspective in cls._SOURCE_PERSPECTIVES.get(
                evidence.source,
                set(),
            ):
                return "PRIMARY"

            return "SUPPORTING"

        for evidence in context.evidence:
            relevance = perspective_relevance(evidence)

            if evidence.evidence_id in direct_ids:
                direct_sections.append(
                    "\n".join(
                        [
                            f"[Direct Evidence {direct_index}]",
                            "Type: DIRECT EVIDENCE",
                            f"Perspective relevance: {relevance}",
                            f"ID: {evidence.evidence_id}",
                            f"Source: {evidence.source}",
                            f"Title: {evidence.title}",
                            f"Text: {evidence.text}",
                        ]
                    )
                )

                direct_index += 1

            elif evidence.evidence_id in contextual_ids:
                contextual_sections.append(
                    "\n".join(
                        [
                            f"[Contextual Evidence {contextual_index}]",
                            "Type: CONTEXTUAL EVIDENCE",
                            f"Perspective relevance: {relevance}",
                            f"ID: {evidence.evidence_id}",
                            f"Source: {evidence.source}",
                            f"Title: {evidence.title}",
                            f"Text: {evidence.text}",
                        ]
                    )
                )

                contextual_index += 1

            else:
                contextual_sections.append(
                    "\n".join(
                        [
                            f"[Contextual Evidence {contextual_index}]",
                            "Type: CONTEXTUAL EVIDENCE",
                            f"Perspective relevance: {relevance}",
                            f"ID: {evidence.evidence_id}",
                            f"Source: {evidence.source}",
                            f"Title: {evidence.title}",
                            f"Text: {evidence.text}",
                        ]
                    )
                )

                contextual_index += 1

        direct_text = (
            "\n\n".join(direct_sections)
            if direct_sections
            else "No direct evidence was identified."
        )

        contextual_text = (
            "\n\n".join(contextual_sections)
            if contextual_sections
            else "No contextual evidence was identified."
        )

        return (
            "USER QUERY — THIS IS THE QUESTION YOU MUST ANSWER:\n"
            f"{context.query}\n\n"

            "CURRENT ANALYSIS PERSPECTIVE:\n"
            f"{perspective.value}\n\n"

            "QUERY-SPECIFICITY REQUIREMENT:\n"
            "Answer the USER QUERY directly from the CURRENT ANALYSIS "
            "PERSPECTIVE.\n"
            "Explicitly address named countries, actors, locations, "
            "events, and issues from the query whenever the supplied "
            "evidence supports doing so.\n"
            "Do not produce a generic conflict explanation that could "
            "apply equally to unrelated conflicts.\n\n"

            "DIRECT EVIDENCE:\n"
            "The following evidence has been classified as directly "
            "relevant to the queried situation. Use this evidence for "
            "situation-specific claims.\n\n"
            f"{direct_text}\n\n"

            "CONTEXTUAL EVIDENCE:\n"
            "The following evidence is contextual only. It may be used "
            "for general background or historical comparison.\n\n"
            f"{contextual_text}\n\n"

            "ANALYSIS TASK:\n"
            f"Produce a concise {perspective.value} analysis that "
            "directly answers the USER QUERY.\n"
            "Keep the military, legal, and historical perspectives "
            "distinct.\n"
            "For the military perspective, focus on military and "
            "operational dynamics rather than providing a generic "
            "legal explanation.\n"
            "For the legal perspective, focus on legal standards, "
            "civilian protection, and legal assessment rather than "
            "providing a generic historical summary.\n"
            "For the historical perspective, focus on chronology, "
            "precedents, conflict patterns, and historical developments "
            "rather than providing a generic legal explanation.\n\n"

            "FINAL EVIDENCE-USE RULES:\n"
            "1. Treat DIRECT EVIDENCE as evidence specifically relevant "
            "to the queried situation.\n"
            "2. Base situation-specific conclusions ONLY on DIRECT "
            "EVIDENCE.\n"
            "3. Treat CONTEXTUAL EVIDENCE only as general background, "
            "historical comparison, or explanation of broader concepts.\n"
            "4. Contextual evidence MUST NOT be used as proof that an "
            "event, actor, agreement, date, obligation, legal rule, "
            "or outcome occurred or applies in the queried situation.\n"
            "5. Do not transfer facts, actors, dates, agreements, "
            "events, military actions, legal obligations, or conclusions "
            "from a different country pair, conflict, border, location, "
            "or historical event to the query.\n"
            "6. If contextual evidence concerns a different country pair "
            "or conflict, explicitly identify that difference.\n"
            "7. Do NOT state or imply that a contextual agreement, rule, "
            "or mechanism applies to the queried situation unless the "
            "provided DIRECT EVIDENCE explicitly establishes that "
            "applicability.\n"
            "8. Do not use general world knowledge to fill missing "
            "information.\n"
            "9. Do not introduce historical events, agreements, legal "
            "articles, military facts, actors, dates, or recommendations "
            "that are not supported by the supplied evidence.\n"
            "10. Do not treat assumptions in the query as independently "
            "verified events unless the evidence confirms them.\n"
            "11. If DIRECT EVIDENCE is insufficient, explicitly state "
            "that the evidence is insufficient.\n"
            "12. Clearly distinguish evidence-supported facts from "
            "interpretation or comparison.\n"
            "13. Generate only 2 to 4 atomic factual claims.\n"
            "14. Each claim should correspond to ONE DIRECT EVIDENCE "
            "record and ONE specific fact.\n"
            "15. Copy dates, locations, actors, fatality counts, "
            "targets, and event descriptions exactly from the evidence.\n"
            "16. Do not calculate, aggregate, reinterpret, or generalize "
            "facts across evidence records.\n"
            "17. Do not modify dates or convert dates into times.\n"
            "18. Do not generate recommendations, opinions, generic "
            "statements, legal conclusions, motivations, intentions, "
            "or unsupported causal claims.\n"
            "19. If insufficient evidence exists, generate fewer claims "
            "rather than inventing claims.\n"
            "20. Every generated claim must be independently checkable "
            "against one DIRECT EVIDENCE record.\n\n"

            "Return the requested JSON structure only."
        )