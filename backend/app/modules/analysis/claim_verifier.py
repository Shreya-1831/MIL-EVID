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
    """Verify multiple generated claims against relevant evidence."""

    MAX_EVIDENCE_PER_CLAIM = 2

    def __init__(self, llm_client: OllamaClient) -> None:
        self._llm_client = llm_client

    def verify(
        self,
        *,
        claims: tuple[str, ...],
        evidence: tuple[AnalysisEvidence, ...],
    ) -> tuple[ClaimVerificationResult, ...]:
        """Verify all claims using a single batch LLM call."""

        if not claims:
            return ()

        if not evidence:
            return tuple(
                self._unsupported_result(claim.strip())
                for claim in claims
            )

        prepared: list[
            tuple[int, str, tuple[AnalysisEvidence, ...]] | None
        ] = []

        for index, raw_claim in enumerate(claims, start=1):
            claim = raw_claim.strip()

            if not claim or self._is_malformed_temporal_claim(claim):
                prepared.append(None)
                continue

            relevant = self._select_relevant_evidence(
                claim=claim,
                evidence=evidence,
            )

            prepared.append(
                (
                    index,
                    claim,
                    relevant,
                )
            )

        valid_items = [
            item
            for item in prepared
            if item is not None
        ]

        if not valid_items:
            return tuple(
                self._unsupported_result(claim.strip())
                for claim in claims
            )

        logger.info(
            "Batch claim verification: %d claim(s) using 1 LLM call.",
            len(valid_items),
        )

        batch_results = self._batch_verify(valid_items)

        results: list[ClaimVerificationResult] = []

        for index, raw_claim in enumerate(claims, start=1):
            claim = raw_claim.strip()

            if (
                not claim
                or self._is_malformed_temporal_claim(claim)
            ):
                results.append(
                    self._unsupported_result(claim)
                )
                continue

            result = batch_results.get(index)

            if result is None:
                results.append(
                    self._unsupported_result(claim)
                )
            else:
                results.append(result)

        final_results = self.deduplicate_claims(
            results=tuple(results)
        )

        logger.info(
            "Claim verification completed: %d result(s).",
            len(final_results),
        )

        return final_results

    def _batch_verify(
        self,
        items: list[
            tuple[int, str, tuple[AnalysisEvidence, ...]]
        ],
    ) -> dict[int, ClaimVerificationResult]:
        """Verify all prepared claims in one structured LLM call."""

        system_prompt = (
            "You are a strict claim-evidence verification system "
            "for MIL-EVID.\n\n"
            "You will receive multiple factual claims and their "
            "relevant evidence.\n"
            "Verify EACH claim independently.\n\n"
            "Use ONLY the supplied evidence.\n"
            "Do NOT use general world knowledge.\n"
            "Do NOT infer missing facts.\n"
            "Do NOT assume a claim is true.\n"
            "Do NOT combine unrelated evidence records.\n\n"
            "SUPPORTED:\n"
            "The supplied evidence directly supports the entire claim.\n\n"
            "PARTIALLY_SUPPORTED:\n"
            "The evidence supports only part of the claim, or an "
            "important detail is not fully supported.\n\n"
            "UNSUPPORTED:\n"
            "The supplied evidence does not sufficiently support "
            "the claim.\n\n"
            "IMPORTANT RULES:\n"
            "1. Check every claim against its supplied evidence.\n"
            "2. Only use evidence IDs belonging to that claim.\n"
            "3. Never invent evidence IDs.\n"
            "4. A SUPPORTED claim requires at least one directly "
            "supporting evidence ID.\n"
            "5. Do not treat different events as contradictory.\n"
            "6. Do not combine facts from unrelated events.\n"
            "7. Exact dates, numbers, locations, and actors must be "
            "supported by the evidence.\n"
            "8. If evidence is insufficient, use UNSUPPORTED.\n\n"
            "Return exactly one result for every claim.\n"
            "claim_index must match the supplied claim number.\n\n"
            "support_score must be between 0.0 and 1.0.\n"
            "status must be exactly one of SUPPORTED, "
            "PARTIALLY_SUPPORTED, UNSUPPORTED."
        )

        claim_sections: list[str] = []

        for index, claim, relevant in items:
            evidence_sections: list[str] = []

            for evidence_item in relevant:
                evidence_sections.append(
                    "\n".join(
                        [
                            f"ID: {evidence_item.evidence_id}",
                            f"Source: {evidence_item.source}",
                            f"Title: {evidence_item.title}",
                            f"Date: {evidence_item.date}",
                            f"Text: {evidence_item.text}",
                        ]
                    )
                )

            claim_sections.append(
                "\n".join(
                    [
                        f"CLAIM {index}",
                        claim,
                        "",
                        "EVIDENCE:",
                        "\n\n".join(evidence_sections),
                    ]
                )
            )

        user_prompt = (
            "Verify the following claims independently.\n\n"
            + "\n\n".join(claim_sections)
            + "\n\n"
            "Return one verification result for every claim."
        )

        schema = {
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "claim_index": {
                                "type": "integer",
                                "minimum": 1,
                            },
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
                            "claim_index",
                            "supporting_evidence_ids",
                            "support_score",
                            "status",
                        ],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["results"],
            "additionalProperties": False,
        }

        try:
            response = self._llm_client.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=schema,
            )
        except Exception:
            logger.exception(
                "Batch claim verification failed."
            )
            return {}

        raw_results = response.get("results", [])

        if not isinstance(raw_results, list):
            logger.warning(
                "Claim verification returned an invalid results list."
            )
            return {}

        result_map: dict[
            int,
            ClaimVerificationResult,
        ] = {}

        items_by_index = {
            index: (claim, relevant)
            for index, claim, relevant in items
        }

        for raw_result in raw_results:
            if not isinstance(raw_result, dict):
                continue

            try:
                claim_index = int(
                    raw_result["claim_index"]
                )

                support_score = float(
                    raw_result["support_score"]
                )

                status = ClaimVerificationStatus(
                    str(
                        raw_result["status"]
                    ).strip().lower()
                )

                raw_ids = raw_result[
                    "supporting_evidence_ids"
                ]

                if not isinstance(raw_ids, list):
                    continue

            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                continue

            if claim_index not in items_by_index:
                continue

            if not 0.0 <= support_score <= 1.0:
                continue

            claim, relevant = items_by_index[claim_index]

            valid_ids = {
                item.evidence_id
                for item in relevant
            }

            supporting_ids = tuple(
                str(evidence_id)
                for evidence_id in raw_ids
                if str(evidence_id) in valid_ids
            )

            if (
                status == ClaimVerificationStatus.SUPPORTED
                and not supporting_ids
            ):
                status = ClaimVerificationStatus.UNSUPPORTED
                support_score = 0.0

            verified = (
                status == ClaimVerificationStatus.SUPPORTED
                and bool(supporting_ids)
                and support_score > 0.0
            )

            result_map[claim_index] = ClaimVerificationResult(
                claim=claim,
                supporting_evidence_ids=supporting_ids,
                support_score=support_score,
                status=status,
                verified=verified,
            )

        return result_map

    @staticmethod
    def _unsupported_result(
        claim: str,
    ) -> ClaimVerificationResult:
        """Create a conservative unsupported result."""

        return ClaimVerificationResult(
            claim=claim,
            supporting_evidence_ids=(),
            support_score=0.0,
            status=ClaimVerificationStatus.UNSUPPORTED,
            verified=False,
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
        """Select the most relevant evidence for a claim."""

        scored: list[
            tuple[float, AnalysisEvidence]
        ] = []

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
            for score, item in scored[
                : cls.MAX_EVIDENCE_PER_CLAIM
            ]
            if score > 0.0
        ]

        if not selected and evidence:
            selected = [evidence[0]]

        return tuple(selected)

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Create normalized tokens."""

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
            claim_tokens.intersection(
                evidence_tokens
            )
        ) / len(claim_tokens)

    @staticmethod
    def _extract_numbers(
        text: str,
    ) -> set[str]:
        """Extract numeric factual values."""

        return set(
            re.findall(
                r"\b\d+(?:\.\d+)?\b",
                text.lower(),
            )
        )

    @staticmethod
    def _extract_factual_terms(
        text: str,
    ) -> set[str]:
        """Extract important factual terms."""

        important_terms = {
            "india", "pakistan", "israel", "palestine",
            "ukraine", "russia", "china", "united kingdom",
            "united states", "france", "germany", "colombia",
            "afghanistan", "kharkiv", "kherson", "donetsk",
            "sialkot", "civilian", "civilians", "residential",
            "infrastructure", "attack", "attacks", "fatality",
            "fatalities", "killed", "injured", "government",
            "military", "forces", "artillery", "shelling",
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

    def deduplicate_claims(
        self,
        *,
        results: tuple[ClaimVerificationResult, ...],
    ) -> tuple[ClaimVerificationResult, ...]:
        """Remove exact normalized duplicate claims."""

        seen: dict[
            str,
            ClaimVerificationResult,
        ] = {}

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
                status=(
                    ClaimVerificationStatus.SUPPORTED
                    if (
                        existing.verified
                        or result.verified
                    )
                    else existing.status
                ),
                verified=(
                    existing.verified
                    or result.verified
                ),
            )

        return tuple(seen.values())

    @staticmethod
    def _parse_single_response(
        response: str,
    ) -> dict | None:
        """Parse a single or legacy batch JSON response."""

        if not response or not response.strip():
            return None

        candidates = [response.strip()]

        fenced_match = re.search(
            r"```(?:json)?\s*(.*?)\s*```",
            response,
            re.DOTALL | re.IGNORECASE,
        )

        if fenced_match:
            candidates.append(
                fenced_match.group(1).strip()
            )

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

            return data

        return None