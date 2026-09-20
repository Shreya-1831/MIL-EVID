"""Evidence-grounded multi-perspective analysis (HIGH-QUALITY OPTIMIZED)."""

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor

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
    """Generate detailed, evidence-grounded analysis for each perspective."""

    ANALYSIS_SCHEMA = {
        "type": "object",
        "properties": {
            "analysis": {"type": "string"},
            "claims": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["analysis", "claims"],
        "additionalProperties": False,
    }

    _SOURCE_PERSPECTIVES = {
        "ICRC Customary IHL": {Perspective.LEGAL},
        "ICRC IHL Treaty": {Perspective.LEGAL},
        "UN Peacemaker": {Perspective.HISTORICAL},
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

    _MAX_EVIDENCE = 8
    _MIN_CLAIMS = 2
    _MAX_CLAIMS = 4

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
        """Generate the three perspective analyses concurrently."""

        perspectives = (
            Perspective.MILITARY,
            Perspective.LEGAL,
            Perspective.HISTORICAL,
        )

        contexts = {
            perspective: self._build_perspective_context(
                context=context,
                perspective=perspective,
            )
            for perspective in perspectives
        }

        def run(
            perspective: Perspective,
        ) -> PerspectiveAnalysisResult:
            return self._analyze_perspective(
                context=contexts[perspective],
                perspective=perspective,
            )

        with ThreadPoolExecutor(
            max_workers=3,
            thread_name_prefix="mil-evid-analysis",
        ) as executor:
            futures = {
                perspective: executor.submit(run, perspective)
                for perspective in perspectives
            }

            results = {
                perspective: futures[perspective].result()
                for perspective in perspectives
            }

        return (
            results[Perspective.MILITARY],
            results[Perspective.LEGAL],
            results[Perspective.HISTORICAL],
        )

    @classmethod
    def _build_perspective_context(
        cls,
        *,
        context: EvidenceContext,
        perspective: Perspective,
    ) -> EvidenceContext:
        """Keep only evidence relevant to the requested perspective."""

        if not context.evidence:
            return EvidenceContext(
                query=context.query,
                evidence=(),
                direct_evidence_ids=context.direct_evidence_ids,
                contextual_evidence_ids=context.contextual_evidence_ids,
            )

        direct_ids = set(context.direct_evidence_ids)

        def matches_perspective(
            evidence: AnalysisEvidence,
        ) -> bool:
            if evidence.source in {"UCDP GED", "UCDP Dyadic"}:
                return perspective == Perspective.MILITARY

            if evidence.perspective is not None:
                return evidence.perspective == perspective

            return perspective in cls._SOURCE_PERSPECTIVES.get(
                evidence.source,
                set(),
            )

        direct_relevant = [
            evidence
            for evidence in context.evidence
            if (
                evidence.evidence_id in direct_ids
                and matches_perspective(evidence)
            )
        ]

        contextual_relevant = [
            evidence
            for evidence in context.evidence
            if (
                evidence.evidence_id not in direct_ids
                and matches_perspective(evidence)
            )
        ]

        direct_relevant.sort(
            key=lambda evidence: evidence.reranker_score,
            reverse=True,
        )

        contextual_relevant.sort(
            key=lambda evidence: evidence.reranker_score,
            reverse=True,
        )

        # if direct_relevant:
        #     relevant = direct_relevant
        # elif perspective == Perspective.HISTORICAL:
        #     relevant = []
        # else:
        #     relevant = contextual_relevant

        if direct_relevant:
            relevant = direct_relevant + contextual_relevant
        else:
            relevant = contextual_relevant

        relevant = relevant[: cls._MAX_EVIDENCE]

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
                    f"direct={evidence.evidence_id in direct_ids}, "
                    f"id={evidence.evidence_id}"
                )
                for index, evidence in enumerate(relevant, start=1)
            ),
        )

        return EvidenceContext(
            query=context.query,
            evidence=tuple(relevant),
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

        if not analysis_text.strip():
            logger.warning(
                "Analysis specificity check skipped: empty analysis."
            )
            return

        is_specific, reason = QuerySpecificityChecker.check_analysis(
            query=query,
            analysis=analysis_text,
        )

        if not is_specific:
            logger.warning(
                "Analysis specificity check failed: %s",
                reason,
            )

    @staticmethod
    def _fallback_analysis(
        *,
        context: EvidenceContext,
        perspective: Perspective,
    ) -> tuple[str, tuple[str, ...]]:
        """Produce a detailed extractive fallback."""

        evidence = context.evidence

        if not evidence:
            analysis = (
                f"No {perspective.value} evidence was retrieved for "
                "this query. A situation-specific assessment cannot "
                "be established from the available evidence."
            )
            return analysis, ()

        if perspective == Perspective.MILITARY:
            lead = (
                "From the military perspective, the conflict demonstrates "
                "several documented patterns and events:"
            )
        elif perspective == Perspective.LEGAL:
            lead = (
                "From the legal perspective, International Humanitarian Law "
                "establishes the following applicable principles:"
            )
        else:
            lead = (
                "From the historical perspective, the conflict exhibits "
                "the following documented chronological patterns:"
            )

        statements: list[str] = []
        claims: list[str] = []

        for evidence_item in evidence[:4]:
            text = " ".join(
                evidence_item.text.split()
            ).strip()

            if not text:
                continue

            cleaned_text = re.sub(
                r"\b(?:event\s+)?date\s*:\s*"
                r"(?:00:00\.0|00:00:00\.0|00:00:00)\.?",
                "",
                text,
                flags=re.IGNORECASE,
            )

            cleaned_text = re.sub(
                r"\s{2,}",
                " ",
                cleaned_text,
            ).strip()

            if not cleaned_text:
                continue

            if evidence_item.source in {
                "UCDP GED",
                "UCDP Dyadic",
            }:
                atomic_claims = (
                    EvidenceAnalyzer._extract_ucdp_atomic_claims(
                        cleaned_text
                    )
                )

                if not atomic_claims:
                    atomic_claims = (
                        EvidenceAnalyzer._extract_atomic_claims(
                            cleaned_text
                        )
                    )
            else:
                atomic_claims = (
                    EvidenceAnalyzer._extract_atomic_claims(
                        cleaned_text
                    )
                )

            for claim in atomic_claims:
                if (
                    claim
                    and not EvidenceAnalyzer._is_non_atomic_claim(
                        claim
                    )
                ):
                    claims.append(claim)

            statements.append(
                f"{evidence_item.source} records: {cleaned_text}"
            )

        if not statements:
            return (
                lead
                + " However, the retrieved records contain no usable "
                "text for a grounded assessment."
            ), ()

        analysis = (
            f"{lead}\n"
            + "\n".join(
                f"• {statement}"
                for statement in statements
            )
        )

        return (
            analysis,
            EvidenceAnalyzer._clean_claims(
                tuple(claims)
            ),
        )

    @staticmethod
    def _extract_ucdp_atomic_claims(
        text: str,
    ) -> tuple[str, ...]:
        """Extract atomic factual claims from UCDP-style records."""

        claims: list[str] = []

        patterns = (
            (
                r"(?:the\s+)?event\s+involved\s+(.+?)(?=\.\s+"
                r"(?:the\s+)?event\s+occurred|\.\s+event\s+date|"
                r"\.\s+reported\s+best|\.\s+source\s+record|$)",
                lambda value: f"The event involved {value}.",
            ),
            (
                r"(?:the\s+)?event\s+occurred\s+(.+?)(?=\.\s+"
                r"event\s+date|\.\s+reported\s+best|"
                r"\.\s+source\s+record|$)",
                lambda value: f"The event occurred in {value}.",
            ),
            (
                r"reported\s+best\s+estimate\s+of\s+fatalities\s*:\s*"
                r"(\d+(?:\.\d+)?)",
                lambda value: (
                    f"The record reports a best estimate of "
                    f"{value} fatalities."
                ),
            ),
        )

        for pattern, formatter in patterns:
            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

            if not match:
                continue

            value = " ".join(
                match.group(1).split()
            ).strip(" ,;.")

            if not value:
                continue

            claim = formatter(value)

            if not EvidenceAnalyzer._is_non_atomic_claim(
                claim
            ):
                claims.append(claim)

        return tuple(
            dict.fromkeys(claims)
        )

    @staticmethod
    def _extract_atomic_claims(
        text: str,
    ) -> tuple[str, ...]:
        """Extract conservative atomic claims from evidence text."""

        sentences = re.split(
            r"(?<=[.!?])\s+",
            text,
        )

        claims: list[str] = []

        for sentence in sentences:
            sentence = " ".join(
                sentence.strip().split()
            )

            if not sentence:
                continue

            if len(sentence) < 15:
                continue

            if EvidenceAnalyzer._is_non_atomic_claim(
                sentence
            ):
                continue

            claims.append(sentence)

            if len(claims) >= 4:
                break

        return tuple(claims)

    def _analyze_perspective(
        self,
        *,
        context: EvidenceContext,
        perspective: Perspective,
    ) -> PerspectiveAnalysisResult:
        """Generate detailed analysis and atomic evidence-verifiable claims."""

        system_prompt = self._build_system_prompt(perspective)

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

        claims = self._clean_claims(claims)

        if self._is_unsafe_analysis(
            analysis=analysis_text,
            perspective=perspective,
        ):
            logger.warning(
                "Rejecting unsupported %s analysis synthesis; "
                "using evidence-grounded fallback.",
                perspective.value,
            )

            analysis_text, fallback_claims = self._fallback_analysis(
                context=context,
                perspective=perspective,
            )

            if fallback_claims:
                claims = fallback_claims

        if not analysis_text.strip():
            logger.warning(
                "Empty %s analysis returned by LLM; "
                "using evidence-grounded fallback.",
                perspective.value,
            )

            analysis_text, fallback_claims = self._fallback_analysis(
                context=context,
                perspective=perspective,
            )

            if not claims:
                claims = fallback_claims

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

        if not isinstance(response, dict):
            raise RuntimeError(
                "Structured analysis response must be a dictionary."
            )

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
    def _has_multiple_assertions(claim: str) -> bool:
        """Detect claims containing multiple factual assertions."""

        normalized = " ".join(
            claim.lower().strip().split()
        )

        if not normalized:
            return False

        compound_patterns = (
            r"\b(?:damaged|destroyed|struck|attacked|killed|injured)"
            r".*\band\b.*"
            r"\b(?:damaged|destroyed|struck|attacked|killed|injured)\b",

            r"\b(?:occurred|took place|was reported|were reported)"
            r".*\band\b.*"
            r"\b(?:damaged|destroyed|killed|injured|attacked|struck)\b",

            r"\b(?:damaged|destroyed|killed|injured|attacked|struck)"
            r".*\band\b.*"
            r"\b(?:occurred|took place|was reported|were reported)\b",

            r"\b(?:killed|injured)\b"
            r".*\band\b.*"
            r"\b(?:damaged|destroyed|struck|attacked)\b",

            r"\b(?:because|while|although|but|which)\b",
        )

        return any(
            re.search(
                pattern,
                normalized,
                flags=re.IGNORECASE,
            )
            for pattern in compound_patterns
        )

    @staticmethod
    def _is_non_atomic_claim(claim: str) -> bool:
        """Reject claims that aggregate, generalize, or infer across events."""

        normalized = " ".join(
            claim.lower().strip().split()
        )

        forbidden_patterns = (
            r"\branging from\b",
            r"\bbetween\s+\d+.*\band\s+\d+",
            r"\bvarious incidents\b",
            r"\bseveral incidents\b",
            r"\bacross multiple\b",
            r"\bacross several\b",
            r"\bin total\b",
            r"\boverall\b",
            r"\bcollectively\b",
            r"\brespectively\b",
            r"\bacross the conflict\b",
            r"\bthroughout the conflict\b",
            r"\bthe conflict has\b",
            r"\bthe conflict was\b",
            r"\bthe conflict involved\b",
            r"\bthe conflict occurred\b",
            r"\bthe conflict took place\b",
            r"\bthe conflict started\b",
            r"\bthe conflict began\b",
            r"\bthe conflict ended\b",
            r"\bthe conflict escalated\b",
            r"\bthe conflict de-escalated\b",
            r"\bthe conflict intensified\b",
            r"\bescalated over time\b",
            r"\bdeclined over time\b",
            r"\bincreased over time\b",
            r"\bdecreased over time\b",
            r"\bconsistently reported\b",
            r"\bremained consistent\b",
            r"\bremained unchanged\b",
            r"\bover the years\b",
            r"\bfrom \d{4} to \d{4}\b",
        )

        if any(
            re.search(pattern, normalized)
            for pattern in forbidden_patterns
        ):
            return True

        return EvidenceAnalyzer._has_multiple_assertions(
            normalized
        )

    @classmethod
    def _is_unsafe_analysis(
        cls,
        analysis: str,
        perspective: Perspective,
    ) -> bool:
        """Detect unsupported conflict-wide synthesis."""

        text = " ".join(analysis.lower().split())

        patterns = (
            r"\bthe conflict started\b",
            r"\bthe conflict began\b",
            r"\bthe conflict escalated\b",
            r"\bthe conflict intensified\b",
            r"\bthe conflict has been ongoing since\b",
            r"\bescalated over time\b",
            r"\bintensified over time\b",
        )

        if perspective in (
            Perspective.MILITARY,
            Perspective.HISTORICAL,
        ):
            return any(re.search(pattern, text) for pattern in patterns)

        return False

    @classmethod
    def _clean_claims(
        cls,
        claims: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Keep only concise, atomic, non-duplicated claims."""

        cleaned: list[str] = []
        seen: set[str] = set()

        for claim in claims:
            normalized_claim = " ".join(
                str(claim).strip().split()
            )

            if not normalized_claim:
                continue

            if cls._is_non_atomic_claim(normalized_claim):
                logger.warning(
                    "Rejecting non-atomic generated claim: %r",
                    normalized_claim,
                )
                continue

            key = normalized_claim.casefold()

            if key in seen:
                continue

            seen.add(key)
            cleaned.append(normalized_claim)

            if len(cleaned) >= 4:
                break

        return tuple(cleaned)

    @staticmethod
    def _build_system_prompt(
        perspective: Perspective,
    ) -> str:
        """Build an engaging perspective-specific prompt (OPTIMIZED FOR DETAIL)."""

        perspective_instructions = {
            Perspective.MILITARY: (
                "You are producing a MILITARY ANALYSIS of the conflict. "
                "Generate a detailed, substantive assessment (3-4 sentences minimum) "
                "covering: documented combat operations, military actors involved, "
                "geographic scope of conflict, attack patterns and intensity, "
                "civilian vs military targeting, infrastructure damage, and "
                "evidence-based escalation indicators. "
                "Be specific about what the evidence shows. "
                "If evidence is limited, explain what cannot be determined. "
            ),
            Perspective.LEGAL: (
                "You are producing a LEGAL ANALYSIS of the conflict. "
                "Generate a detailed, substantive assessment (3-4 sentences minimum) "
                "explaining: applicable International Humanitarian Law principles, "
                "obligations regarding distinction (civilian vs military), "
                "proportionality requirements, precautions parties must take, "
                "civilian protection rules, and what the evidence shows about "
                "compliance or violations. Reference specific IHL rules where applicable. "
            ),
            Perspective.HISTORICAL: (
                "You are producing a HISTORICAL ANALYSIS of the conflict. "
                "Generate a detailed, substantive assessment (3-4 sentences minimum) "
                "covering: documented chronology of events, key historical milestones, "
                "major developments and turning points, patterns of conflict behavior "
                "over time, regional context, prior agreements or attempts at resolution, "
                "and long-term trajectory. Use specific dates and events from evidence. "
            ),
        }

        return (
            "You are MIL-EVID, an evidence-grounded military conflict analyzer.\n\n"
            f"PERSPECTIVE: {perspective.value.upper()}\n"
            f"{perspective_instructions[perspective]}\n\n"
            "ANALYSIS REQUIREMENTS:\n"
            "1. Generate 3-4 complete sentences MINIMUM.\n"
            "2. Each sentence must be complete and grammatically correct.\n"
            "3. Do NOT generate one-line summaries or telegraphic responses.\n"
            "4. Be substantive and analytical, not vague.\n"
            "5. Draw on the supplied evidence to support specific points.\n"
            "6. Explain what the evidence does and does NOT establish.\n\n"
            "GROUNDING RULES:\n"
            "1. Use ONLY supplied evidence for factual claims.\n"
            "2. Do not use outside knowledge or assumptions.\n"
            "3. Do not invent facts, dates, locations, or actors.\n"
            "4. State explicitly what cannot be determined from evidence.\n"
            "5. Distinguish documented facts from interpretation.\n\n"
            "CLAIMS:\n"
            "Generate 2-4 atomic claims (one fact per claim).\n"
            "Each claim must be traceable to supplied evidence.\n"
            "Copy exact values (dates, locations, actors, fatalities).\n"
            "Do not aggregate or calculate across events.\n"
            "Keep claims concise (one sentence each).\n\n"
            "OUTPUT FORMAT:\n"
            "Return ONLY valid JSON: {\"analysis\": \"...\", \"claims\": [...]}\n"
            "Ensure 'analysis' field contains complete, detailed sentences.\n"
            "Ensure 'claims' field contains atomic, evidence-backed claims.\n"
        )

    @classmethod
    def _build_user_prompt(
        cls,
        *,
        context: EvidenceContext,
        perspective: Perspective,
    ) -> str:
        """Format a compact query-specific evidence prompt."""

        direct_ids = set(context.direct_evidence_ids)

        evidence_sections: list[str] = []

        for index, evidence in enumerate(context.evidence, start=1):
            is_direct = evidence.evidence_id in direct_ids

            if evidence.source in {"UCDP GED", "UCDP Dyadic"}:
                is_primary = perspective == Perspective.MILITARY
            else:
                is_primary = (
                    evidence.perspective == perspective
                    if evidence.perspective is not None
                    else perspective
                    in cls._SOURCE_PERSPECTIVES.get(
                        evidence.source,
                        set(),
                    )
                )

            relevance = "PRIMARY" if is_primary else "SUPPORTING"

            evidence_sections.append(
                "\n".join(
                    [
                        f"[Evidence {index}] {evidence.source} "
                        f"(score: {evidence.reranker_score:.3f})",
                        f"Direct: {is_direct} | Relevance: {relevance}",
                        f"ID: {evidence.evidence_id}",
                        f"Title: {evidence.title}",
                        f"Text: {evidence.text}",
                    ]
                )
            )

        evidence_text = (
            "\n\n".join(evidence_sections)
            if evidence_sections
            else "No evidence was retrieved."
        )

        if perspective == Perspective.MILITARY:
            task = (
                "Generate a detailed military assessment (3-4+ sentences) covering: "
                "combat operations, military actors, attack patterns, civilian/military "
                "targeting, infrastructure damage, and conflict intensity."
            )
        elif perspective == Perspective.LEGAL:
            task = (
                "Generate a detailed legal assessment (3-4+ sentences) covering: "
                "applicable IHL principles, distinction, proportionality, precautions, "
                "civilian protection rules, and evidence of compliance or violations."
            )
        else:
            task = (
                "Generate a detailed historical assessment (3-4+ sentences) covering: "
                "conflict chronology, key events, milestones, patterns over time, "
                "prior agreements, and trajectory."
            )

        return (
            "SITUATION:\n"
            f"{context.query}\n\n"
            "PERSPECTIVE:\n"
            f"{perspective.value.upper()}\n\n"
            "TASK:\n"
            f"{task}\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "- Generate substantive, detailed analysis (minimum 3-4 complete sentences).\n"
            "- Every sentence must be COMPLETE and grammatically correct.\n"
            "- Do NOT produce one-line summaries.\n"
            "- Do NOT truncate or break sentences.\n"
            "- Use supplied evidence to support specific points.\n"
            "- Explain what evidence does and does NOT establish.\n"
            "- Generate 2-4 atomic claims (one fact per claim).\n"
            "- Each claim: one piece of evidence, one fact, complete sentence.\n"
            "- Copy exact dates/locations/actors from evidence.\n"
            "- Do not aggregate or calculate across events.\n\n"
            "SUPPLIED EVIDENCE:\n"
            f"{evidence_text}\n\n"
            "RESPONSE:\n"
            "Return ONLY valid JSON with 'analysis' (detailed 3-4+ sentences) "
            "and 'claims' (2-4 atomic claims) fields."
        )