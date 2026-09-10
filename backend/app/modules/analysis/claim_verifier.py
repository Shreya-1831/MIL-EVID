"""Claim-evidence verification for MIL-EVID."""

from __future__ import annotations

import json
import logging
import re
from difflib import SequenceMatcher

from app.domain.enums import ClaimVerificationStatus
from app.domain.models.analysis import (
    AnalysisEvidence,
    ClaimVerificationResult,
)
from app.modules.analysis.llm_client import OllamaClient


logger = logging.getLogger("mil_evid")


class ClaimVerifier:
    """Verify generated claims against the most relevant evidence."""

    MAX_EVIDENCE_PER_CLAIM = 2

    def __init__(self, llm_client: OllamaClient) -> None:
        self._llm_client = llm_client

    def verify(
        self,
        *,
        claims: tuple[str, ...],
        evidence: tuple[AnalysisEvidence, ...],
    ) -> tuple[ClaimVerificationResult, ...]:
        """Verify each claim independently against relevant evidence."""

        if not claims:
            return ()

        if not evidence:
            return tuple(
                ClaimVerificationResult(
                    claim=claim,
                    supporting_evidence_ids=(),
                    support_score=0.0,
                    status=ClaimVerificationStatus.UNSUPPORTED,
                    verified=False,
                )
                for claim in claims
            )

        results: list[ClaimVerificationResult] = []

        for index, claim in enumerate(claims, start=1):
            claim = claim.strip()

            if not claim:
                results.append(
                    ClaimVerificationResult(
                        claim=claim,
                        supporting_evidence_ids=(),
                        support_score=0.0,
                        status=ClaimVerificationStatus.UNSUPPORTED,
                        verified=False,
                    )
                )
                continue

            if self._is_malformed_temporal_claim(claim):
                logger.warning(
                    "Rejecting malformed temporal claim: %r",
                    claim,
                )

                results.append(
                    ClaimVerificationResult(
                        claim=claim,
                        supporting_evidence_ids=(),
                        support_score=0.0,
                        status=ClaimVerificationStatus.UNSUPPORTED,
                        verified=False,
                    )
                )
                continue

            relevant_evidence = self._select_relevant_evidence(
                claim=claim,
                evidence=evidence,
            )

            logger.info(
                "Verifying claim %d/%d against %d relevant evidence item(s).",
                index,
                len(claims),
                len(relevant_evidence),
            )

            result = self._verify_single_claim(
                claim_index=index,
                claim=claim,
                evidence=relevant_evidence,
            )

            results.append(result)

        logger.info(
            "Claim verification completed: %d claim(s).",
            len(results),
        )

        return tuple(results)

    def _verify_single_claim(
        self,
        *,
        claim_index: int,
        claim: str,
        evidence: tuple[AnalysisEvidence, ...],
    ) -> ClaimVerificationResult:
        """Verify one claim using only its most relevant evidence."""

        if not evidence:
            return ClaimVerificationResult(
                claim=claim,
                supporting_evidence_ids=(),
                support_score=0.0,
                status=ClaimVerificationStatus.UNSUPPORTED,
                verified=False,
            )

        system_prompt = (
            "You are a strict claim-evidence verification system.\n\n"
            "Your task is to verify ONE factual claim against the "
            "supplied evidence.\n\n"
            "Use ONLY the supplied evidence.\n"
            "Do NOT use general world knowledge.\n"
            "Do NOT infer missing facts.\n"
            "Do NOT assume the claim is true.\n\n"

            "SUPPORTED:\n"
            "The evidence directly supports the entire claim.\n\n"

            "PARTIALLY_SUPPORTED:\n"
            "The evidence supports only part of the claim, or an "
            "important detail in the claim is not fully supported.\n\n"

            "UNSUPPORTED:\n"
            "The evidence does not sufficiently support the claim.\n\n"

            "IMPORTANT:\n"
            "1. Check the claim against the actual evidence text.\n"
            "2. Only select evidence IDs that directly support the claim.\n"
            "3. Never invent evidence IDs.\n"
            "4. If the evidence does not support the claim, return "
            "UNSUPPORTED with an empty evidence list.\n"
            "5. A claim must be fully supported before using SUPPORTED.\n"
            "6. Do not combine unrelated events.\n"
            "7. Do not treat two different events as contradictory merely "
            "because their locations or fatality counts differ.\n\n"

            "Return ONLY valid JSON in exactly this structure:\n"
            "{\n"
            '  "supporting_evidence_ids": [],\n'
            '  "support_score": 0.0,\n'
            '  "status": "UNSUPPORTED"\n'
            "}\n\n"

            "support_score must be a number from 0.0 to 1.0.\n"
            "status must be exactly one of: SUPPORTED, "
            "PARTIALLY_SUPPORTED, UNSUPPORTED."
        )

        evidence_sections: list[str] = []

        for evidence_index, item in enumerate(evidence, start=1):
            evidence_sections.append(
                "\n".join(
                    [
                        f"[Evidence {evidence_index}]",
                        f"ID: {item.evidence_id}",
                        f"Source: {item.source}",
                        f"Title: {item.title}",
                        f"Date: {item.date}",
                        f"Text: {item.text}",
                    ]
                )
            )

        user_prompt = (
            f"CLAIM {claim_index}:\n"
            f"{claim}\n\n"
            "EVIDENCE:\n"
            + "\n\n".join(evidence_sections)
            + "\n\n"
            "Verify the claim strictly against the supplied evidence."
        )

        # ------------------------------------------------------------------
        # Structured LLM output
        # ------------------------------------------------------------------

        try:
            structured_response = self._llm_client.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema={
                    "type": "object",
                    "properties": {
                        "supporting_evidence_ids": {
                            "type": "array",
                            "items": {
                                "type": "string",
                            },
                        },
                        "support_score": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                        "status": {
                            "type": "string",
                            "enum": [
                                "SUPPORTED",
                                "PARTIALLY_SUPPORTED",
                                "UNSUPPORTED",
                            ],
                        },
                    },
                    "required": [
                        "supporting_evidence_ids",
                        "support_score",
                        "status",
                    ],
                    "additionalProperties": False,
                },
            )

        except Exception:
            logger.exception(
                "LLM verification failed for claim %d.",
                claim_index,
            )

            return ClaimVerificationResult(
                claim=claim,
                supporting_evidence_ids=(),
                support_score=0.0,
                status=ClaimVerificationStatus.UNSUPPORTED,
                verified=False,
            )

        # ------------------------------------------------------------------
        # Normalize structured response
        # ------------------------------------------------------------------

        try:
            parsed = {
                "supporting_evidence_ids": tuple(
                    str(evidence_id)
                    for evidence_id in structured_response.get(
                        "supporting_evidence_ids",
                        [],
                    )
                ),
                "support_score": float(
                    structured_response.get(
                        "support_score",
                        0.0,
                    )
                ),
                "status": ClaimVerificationStatus(
                    str(
                        structured_response.get(
                            "status",
                            "UNSUPPORTED",
                        )
                    )
                    .strip()
                    .lower()
                ),
            }

        except (
            TypeError,
            ValueError,
        ):
            logger.warning(
                "Invalid structured verification response for claim %d.",
                claim_index,
            )

            return ClaimVerificationResult(
                claim=claim,
                supporting_evidence_ids=(),
                support_score=0.0,
                status=ClaimVerificationStatus.UNSUPPORTED,
                verified=False,
            )

        valid_evidence_ids = {
            item.evidence_id
            for item in evidence
        }

        supporting_ids = tuple(
            evidence_id
            for evidence_id in parsed["supporting_evidence_ids"]
            if evidence_id in valid_evidence_ids
        )

        status = parsed["status"]
        support_score = parsed["support_score"]

        # ------------------------------------------------------------------
        # Safety validation
        # ------------------------------------------------------------------

        if not 0.0 <= support_score <= 1.0:
            logger.warning(
                "Claim %d returned invalid support score: %s",
                claim_index,
                support_score,
            )

            return ClaimVerificationResult(
                claim=claim,
                supporting_evidence_ids=(),
                support_score=0.0,
                status=ClaimVerificationStatus.UNSUPPORTED,
                verified=False,
            )

        # A SUPPORTED claim must have at least one valid evidence ID.
        if (
            status == ClaimVerificationStatus.SUPPORTED
            and not supporting_ids
        ):
            logger.warning(
                "Claim %d was marked SUPPORTED but contained no valid "
                "evidence IDs. Normalizing to UNSUPPORTED.",
                claim_index,
            )

            return ClaimVerificationResult(
                claim=claim,
                supporting_evidence_ids=(),
                support_score=0.0,
                status=ClaimVerificationStatus.UNSUPPORTED,
                verified=False,
            )

        verified = (
            status == ClaimVerificationStatus.SUPPORTED
            and bool(supporting_ids)
            and support_score > 0.0
        )

        logger.info(
            "Claim %d verification: status=%s score=%.2f evidence_count=%d",
            claim_index,
            status.value.upper(),
            support_score,
            len(supporting_ids),
        )

        return ClaimVerificationResult(
            claim=claim,
            supporting_evidence_ids=supporting_ids,
            support_score=support_score,
            status=status,
            verified=verified,
        )

    @staticmethod
    def _is_malformed_temporal_claim(
        claim: str,
    ) -> bool:
        """Detect obviously malformed date/time claims."""

        normalized = claim.lower()

        malformed_patterns = (
            "00:00.0",
            "00:00:00.0",
            "00:00:00",
        )

        return any(
            pattern in normalized
            for pattern in malformed_patterns
        )

    @classmethod
    def _select_relevant_evidence(
        cls,
        *,
        claim: str,
        evidence: tuple[AnalysisEvidence, ...],
    ) -> tuple[AnalysisEvidence, ...]:
        """Select evidence using lexical, factual, and semantic signals."""

        scored: list[tuple[float, AnalysisEvidence]] = []

        claim_tokens = cls._tokenize(claim)
        claim_numbers = cls._extract_numbers(claim)
        claim_entities = cls._extract_factual_terms(claim)

        for item in evidence:
            text = " ".join(
                [
                    str(item.title),
                    str(item.date),
                    str(item.text),
                ]
            )

            evidence_tokens = cls._tokenize(text)
            evidence_numbers = cls._extract_numbers(text)
            evidence_entities = cls._extract_factual_terms(text)

            token_overlap = cls._token_overlap(
                claim_tokens,
                evidence_tokens,
            )

            number_match = cls._set_overlap(
                claim_numbers,
                evidence_numbers,
            )

            factual_term_match = cls._set_overlap(
                claim_entities,
                evidence_entities,
            )

            sequence_score = SequenceMatcher(
                None,
                claim.lower(),
                text.lower(),
            ).ratio()

            score = (
                token_overlap * 0.45
                + factual_term_match * 0.30
                + number_match * 0.20
                + sequence_score * 0.05
            )

            scored.append((score, item))

        scored.sort(
            key=lambda pair: pair[0],
            reverse=True,
        )

        selected = [
            item
            for score, item in scored[: cls.MAX_EVIDENCE_PER_CLAIM]
            if score > 0.0
        ]

        if not selected and evidence:
            selected = [evidence[0]]

        return tuple(selected)

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Create simple normalized tokens for evidence matching."""

        return {
            token
            for token in re.findall(
                r"[a-zA-Z0-9]+",
                text.lower(),
            )
            if len(token) > 2
        }

    @staticmethod
    def _token_overlap(
        claim_tokens: set[str],
        evidence_tokens: set[str],
    ) -> float:
        """Calculate normalized token overlap."""

        if not claim_tokens:
            return 0.0

        return len(
            claim_tokens.intersection(evidence_tokens)
        ) / len(claim_tokens)

    @staticmethod
    def _extract_numbers(text: str) -> set[str]:
        """Extract numeric factual values from text."""

        return set(
            re.findall(
                r"\b\d+(?:\.\d+)?\b",
                text.lower(),
            )
        )

    @staticmethod
    def _extract_factual_terms(text: str) -> set[str]:
        """Extract important factual terms such as actors and locations."""

        important_terms = {
            "india", "pakistan", "israel", "palestine", "ukraine", "russia",
            "china", "united kingdom", "united states", "france", "germany",
            "colombia", "afghanistan",
            "kharkiv", "kherson", "donetsk", "sialkot",
            "civilian", "civilians", "residential", "infrastructure",
            "attack", "attacks", "fatality", "fatalities", "killed", "injured",
            "government", "military", "forces", "artillery", "shelling",
            "airstrike", "missile", "escalation", "conflict",
        }

        normalized = text.lower()

        return {
            term
            for term in important_terms
            if re.search(
                rf"\b{re.escape(term)}\b",
                normalized,
            )
        }

    def deduplicate_claims(
        self,
        *,
        results: tuple[ClaimVerificationResult, ...],
    ) -> tuple[ClaimVerificationResult, ...]:
        """Remove exact normalized duplicate claims."""

        seen: dict[str, ClaimVerificationResult] = {}

        for result in results:
            normalized = " ".join(
                result.claim.lower().strip().split()
            )

            if normalized not in seen:
                seen[normalized] = result
                continue

            existing = seen[normalized]

            merged_evidence_ids = tuple(
                dict.fromkeys(
                    (
                        *existing.supporting_evidence_ids,
                        *result.supporting_evidence_ids,
                    )
                )
            )

            seen[normalized] = ClaimVerificationResult(
                claim=existing.claim,
                supporting_evidence_ids=merged_evidence_ids,
                support_score=max(
                    existing.support_score,
                    result.support_score,
                ),
                status=existing.status,
                verified=existing.verified,
            )

        return tuple(seen.values())

    @staticmethod
    def _set_overlap(
        first: set[str],
        second: set[str],
    ) -> float:
        """Calculate overlap relative to the first set."""

        if not first:
            return 0.0

        return len(
            first.intersection(second)
        ) / len(first)

    @staticmethod
    def _parse_single_response(
        response: str,
    ) -> dict | None:
        """Parse a single JSON verification response.

        Supports both the new single-result format and the legacy
        batch-result format used by existing tests and LLM responses.
        """

        if not response or not response.strip():
            return None

        response = response.strip()

        candidates: list[str] = [response]

        # Handle accidental Markdown code fences.
        fenced_match = re.search(
            r"```(?:json)?\s*(.*?)\s*```",
            response,
            re.DOTALL | re.IGNORECASE,
        )

        if fenced_match:
            candidates.append(
                fenced_match.group(1).strip()
            )

        # Handle extra text surrounding the JSON object.
        object_match = re.search(
            r"\{.*\}",
            response,
            re.DOTALL,
        )

        if object_match:
            candidates.append(
                object_match.group(0).strip()
            )

        for candidate in candidates:
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError:
                continue

            if not isinstance(data, dict):
                continue

            # ---------------------------------------------------------
            # New single-result format:
            #
            # {
            #   "supporting_evidence_ids": ["e1"],
            #   "support_score": 0.95,
            #   "status": "SUPPORTED"
            # }
            # ---------------------------------------------------------
            if "results" not in data:
                parsed = ClaimVerifier._parse_result_object(data)

                if parsed is not None:
                    return parsed

                continue

            # ---------------------------------------------------------
            # Legacy batch format:
            #
            # {
            #   "results": [
            #       {
            #           "claim_index": 1,
            #           "supporting_evidence_ids": ["e1"],
            #           "support_score": 0.95,
            #           "status": "SUPPORTED"
            #       }
            #   ]
            # }
            #
            # We are verifying one claim at a time, so use the first
            # valid result returned by the LLM.
            # ---------------------------------------------------------
            raw_results = data.get("results")

            if not isinstance(raw_results, list):
                continue

            for item in raw_results:
                if not isinstance(item, dict):
                    continue

                parsed = ClaimVerifier._parse_result_object(item)

                if parsed is not None:
                    return parsed

        return None

    @staticmethod
    def _parse_result_object(
        data: dict,
    ) -> dict | None:
        """Validate and normalize one verification result."""

        raw_ids = data.get(
            "supporting_evidence_ids",
            [],
        )

        if not isinstance(raw_ids, list):
            return None

        try:
            supporting_ids = tuple(
                str(evidence_id)
                for evidence_id in raw_ids
            )

            support_score = float(
                data.get(
                    "support_score",
                    0.0,
                )
            )

            status = ClaimVerificationStatus(
                str(
                    data.get(
                        "status",
                        "UNSUPPORTED",
                    )
                )
                .strip()
                .lower()
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

        if not 0.0 <= support_score <= 1.0:
            return None

        return {
            "supporting_evidence_ids": supporting_ids,
            "support_score": support_score,
            "status": status,
        }