"""Evidence-grounded multi-perspective analysis."""

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
    """Generate concise, evidence-grounded analysis for each perspective."""

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
    # _MAX_EVIDENCE = 5
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
            max_workers=2,
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
            if evidence.perspective == perspective:
                return True

            return perspective in cls._SOURCE_PERSPECTIVES.get(
                evidence.source,
                set(),
            )

        relevant = [
            evidence
            for evidence in context.evidence
            if matches_perspective(evidence)
        ]

        relevant.sort(
            key=lambda evidence: evidence.reranker_score,
            reverse=True,
        )

        # Keep the LLM evidence view bounded.
        # Retrieval and reranking are unchanged.
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
        """
        Produce a minimal extractive answer when Ollama returns no
        usable analysis.

        This fallback deliberately does not infer facts. It only reports
        the supplied evidence and explicitly identifies limitations.
        """

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
                "From the military perspective, the retrieved evidence "
                "documents the following conflict-related records:"
            )
        elif perspective == Perspective.LEGAL:
            lead = (
                "From the legal perspective, the retrieved evidence "
                "provides the following international humanitarian law "
                "material:"
            )
        else:
            lead = (
                "From the historical perspective, the retrieved evidence "
                "documents the following historical or conflict records:"
            )

        statements: list[str] = []
        claims: list[str] = []

        for evidence_item in evidence[:4]:
            text = " ".join(evidence_item.text.split()).strip()

            if not text:
                continue

            statements.append(
                f"{evidence_item.source} ({evidence_item.evidence_id}) "
                f"records: {text}"
            )

            claims.append(text)

        if not statements:
            return (
                lead
                + " However, the retrieved records contain no usable "
                "text for a grounded assessment."
            ), ()

        limitation = (
            "The supplied evidence does not by itself establish facts "
            "that are absent from these records, and no unsupported "
            "conclusion is drawn."
        )

        analysis = (
            f"{lead}\n"
            + "\n".join(
                f"- {statement}"
                for statement in statements
            )
            + f"\n\n{limitation}"
        )

        return (
            analysis,
            EvidenceAnalyzer._clean_claims(tuple(claims)),
        )

    def _analyze_perspective(
        self,
        *,
        context: EvidenceContext,
        perspective: Perspective,
    ) -> PerspectiveAnalysisResult:
        """Generate analysis and atomic evidence-verifiable claims."""

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

        return any(
            re.search(pattern, normalized)
            for pattern in forbidden_patterns
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
        """Build a strict perspective-specific grounding prompt."""

        perspective_instructions = {
            Perspective.MILITARY: (
                "You are producing ONLY the MILITARY section. "
                "Discuss documented military events, actors, "
                "locations, attacks, fatalities, conflict intensity, "
                "military developments, and evidence-supported "
                "escalation indicators. "
                "Treat every factual statement in the USER QUERY as an "
                "issue to assess, not as evidence that the event actually "
                "occurred. "
                "If the supplied evidence does not explicitly document "
                "attacks on civilian areas, damage to essential "
                "infrastructure, civilian protection incidents, or "
                "responsibility for a specific attack, say that the "
                "evidence does not establish that point. "
                "Do not infer escalation merely by combining separate "
                "events or records from different dates. "
                "Do not write a legal section or historical section."
            ),
            Perspective.LEGAL: (
                "You are producing ONLY the LEGAL section. "
                "Discuss international humanitarian law, distinction, "
                "proportionality, precautions, civilian protection, "
                "and the limits of the supplied legal evidence. "
                "Do not write a military section or historical section."
            ),
            Perspective.HISTORICAL: (
                "You are producing ONLY the HISTORICAL section. "
                "Discuss chronology, documented historical events, "
                "conflict records, patterns, and changes over time "
                "that appear in the supplied evidence. "
                "Treat each retrieved record as a separate record unless "
                "the evidence itself explicitly establishes that the records "
                "describe the same event or a temporal sequence. "
                "Do not infer the beginning, end, or duration of a conflict "
                "merely from the earliest or latest year appearing in the "
                "retrieved records. "
                "An earliest retrieved event is not necessarily the conflict "
                "start date. Only state that a conflict started in a particular "
                "year if a supplied evidence record explicitly states that. "
                "Do not infer escalation, continuity, consistency, or trends "
                "merely by comparing separate retrieved records. "
                "Only state that a conflict escalated over time if the supplied "
                "evidence explicitly documents such an escalation or provides "
                "a clearly established temporal comparison. "
                "Do not write a military section or legal section."
            ),
        }

        return (
            "You are MIL-EVID, an evidence-grounded military situation "
            "analysis system.\n\n"
            f"CURRENT PERSPECTIVE: {perspective.value}\n"
            f"{perspective_instructions[perspective]}\n\n"
            "HARD SCOPE RULES:\n"
            "1. Answer ONLY the current perspective.\n"
            "2. Do not answer the complete multi-perspective query.\n"
            "3. Do not create sections for other perspectives.\n"
            "4. Do not write phrases such as 'from a military "
            "perspective', 'from a legal perspective', or 'from a "
            "historical perspective' unless they refer to the current "
            "perspective.\n"
            "5. Do not repeat the user's entire question.\n"
            "6. If the evidence is insufficient, say exactly what "
            "cannot be established.\n\n"
            "GROUNDING RULES:\n"
            "1. Use only the supplied evidence for factual claims.\n"
            "2. Do not use outside knowledge.\n"
            "3. Do not invent facts, dates, locations, actors, "
            "fatalities, attacks, intentions, or causes.\n"
            "4. Do not present unsupported assumptions as facts.\n"
            "5. Do not treat assumptions in the query as verified facts.\n"
            "6. Distinguish documented facts from analytical "
            "interpretation.\n"
            "7. Never transfer facts from another conflict, location, "
            "actor pair, or historical period.\n"
            "8. Never transfer facts from a different country pair or "
            "different conflict into the queried situation.\n"
            "9. Never transfer facts from a different historical event "
            "or time period.\n\n"
            "PERSPECTIVE RULES:\n"
            "- Military: do not infer military intentions, "
            "capabilities, deployments, tactics, or causes of "
            "escalation unless explicitly supported.\n"
            "- Legal: explain legal rules when supported, but do not "
            "conclude that a particular attack was unlawful unless "
            "the supplied evidence contains sufficient event-specific "
            "facts for that conclusion.\n"
            "- Historical: do not introduce historical background "
            "from general knowledge. Do not mention Crimea 2014, "
            "Minsk, NATO, previous invasions, or other background "
            "unless present in the supplied evidence.\n\n"
            "CLAIMS:\n"
            f"Generate up to {EvidenceAnalyzer._MAX_CLAIMS} atomic claims "
            "when possible.\n"
            "Each claim must contain exactly one independently "
            "verifiable fact from one supplied evidence record.\n"
            "Each generated claim must be traceable to one supplied "
            "evidence record.\n"
            "Copy factual values exactly.\n"
            "Never aggregate multiple events.\n"
            "Never calculate ranges or totals.\n"
            "Never create broad claims about the entire conflict from "
            "one event.\n"
            "If there are not enough directly supported facts, generate "
            "fewer claims.\n\n"
            "IMPORTANT DATE RULE:\n"
            "If an evidence record contains a date, preserve the date "
            "exactly as written.\n"
            "Preserve the date exactly as written.\n"
            "Never convert dates or timestamps into times.\n"
            "If the date is unclear or malformed, do not invent or "
            "normalize it and do not include it in a claim.\n"
            "Do not modify dates.\n\n"
            "OUTPUT:\n"
            "Return ONLY valid JSON matching the supplied schema.\n"
            "The 'analysis' field must contain a non-empty answer "
            "when usable evidence is supplied."
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

            relevance = (
                "PRIMARY"
                if (
                    evidence.perspective == perspective
                    or perspective
                    in cls._SOURCE_PERSPECTIVES.get(
                        evidence.source,
                        set(),
                    )
                )
                else "SUPPORTING"
            )

            evidence_sections.append(
                "\n".join(
                    [
                        f"[Evidence {index}]",
                        f"Type: {'DIRECT' if is_direct else 'CONTEXTUAL'}",
                        f"Perspective: {relevance}",
                        f"ID: {evidence.evidence_id}",
                        f"Source: {evidence.source}",
                        f"Title: {evidence.title}",
                        f"Reranker score: "
                        f"{evidence.reranker_score:.4f}",
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
                "Assess only the military dimension. Identify "
                "documented conflict events, actors, locations, "
                "fatalities, intensity, military developments, and "
                "evidence-supported escalation indicators."
            )
        elif perspective == Perspective.LEGAL:
            task = (
                "Assess only the legal dimension. Explain the "
                "applicable IHL principles and what the supplied "
                "evidence does or does not establish about civilian "
                "protection, distinction, proportionality, and "
                "precautions."
            )
        else:
            task = (
                "Assess only the historical dimension. Describe the "
                "chronology, historical records, conflict patterns, "
                "and changes over time that are explicitly present "
                "in the supplied evidence."
            )

        return (
            "USER QUERY:\n"
            f"{context.query}\n\n"
            "ANALYSIS PERSPECTIVE:\n"
            f"{perspective.value}\n\n"
            "TASK:\n"
            f"{task}\n\n"
            "IMPORTANT:\n"
            "Answer only this perspective. Do not produce military, "
            "legal, and historical sections inside one response.\n"
            "Use only the evidence supplied below.\n"
            "Do not use outside knowledge.\n"
            "Do not present unsupported assumptions as facts.\n"
            "Do not assume that statements in the query are verified "
            "facts.\n"
            "If the evidence cannot establish something requested by "
            "the user, explicitly state the limitation.\n\n"
            "LEGAL SAFETY RULE:\n"
            "A legal principle can be explained when supported by the "
            "ICRC evidence, but do not conclude that a particular "
            "attack was unlawful unless the supplied evidence contains "
            "sufficient facts for that conclusion.\n"
            "A legal principle and an attack being unlawful are "
            "different claims.\n\n"
            "HISTORICAL SAFETY RULE:\n"
            "Do not introduce historical background from general "
            "knowledge. For example, do not introduce Crimea 2014, "
            "Minsk, NATO, previous invasions, or other historical "
            "events unless they appear in the supplied evidence.\n\n"
            "MILITARY SAFETY RULE:\n"
            "Do not infer military intentions, capabilities, tactics, "
            "deployments, or escalation causes unless supported by the "
            "supplied evidence.\n\n"
            "CROSS-CONFLICT RULE:\n"
            "Do not transfer facts from a different country pair, "
            "different conflict, location, actor pair, historical "
            "event, or time period into the queried situation.\n"
            "Do not transfer facts from another conflict into the "
            "queried situation.\n"
            "A contextual source may explain general background, but "
            "must not be treated as proof that an event or fact applies "
            "to the queried situation.\n"
            "Different country pairs and conflicts must remain "
            "explicitly separated.\n\n"
            "CLAIM RULE:\n"
            "Each generated claim must be traceable to one supplied "
            "evidence record.\n"
            "Every claim must contain exactly one independently "
            "verifiable fact.\n"
            "Do not create a claim merely because it sounds plausible.\n"
            "Copy dates, locations, actors, fatality counts, and event "
            "descriptions exactly as supported by the evidence.\n"
            "Do not calculate, aggregate, reinterpret, or generalize "
            "facts across evidence records.\n"
            "If a date or timestamp is malformed, do not reproduce it "
            "as a time and do not invent a replacement.\n\n"
            "EVIDENCE:\n"
            f"{evidence_text}\n\n"
            "Return ONLY the requested JSON object."
        )