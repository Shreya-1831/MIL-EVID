"""Evidence contradiction detection for MIL-EVID."""

from __future__ import annotations

import json
import logging
import re

from app.domain.enums import ContradictionStatus, ContradictionType
from app.domain.models.analysis import (
    AnalysisEvidence,
    ContradictionResult,
)
from app.modules.analysis.llm_client import OllamaClient


logger = logging.getLogger("mil_evid")


class ContradictionDetector:
    """Detect contradictions between the most relevant evidence items."""

    # MAX_COMPARISONS = 6
    MAX_COMPARISONS = 3

    # UCDP Dyadic records commonly encode the dyad and annual record
    # year directly in the evidence ID, for example:
    # ucdp-dyadic-14117-2025::chunk-0000
    _UCDP_DYADIC_ID_PATTERN = re.compile(
        r"^ucdp-dyadic-(?P<dyad>.+)-(?P<year>\d{4})::",
        re.IGNORECASE,
    )

    _UCDP_GED_ID_PATTERN = re.compile(
        r"^ucdp-ged-(?P<event_id>\d+)::",
        re.IGNORECASE,
    )

    _ACLED_ID_PATTERN = re.compile(
        r"^acled-(?P<event_id>[^:]+)",
        re.IGNORECASE,
    )

    def __init__(self, llm_client: OllamaClient) -> None:
        self._llm_client = llm_client

    def detect(
        self,
        *,
        evidence: tuple[AnalysisEvidence, ...],
    ) -> tuple[ContradictionResult, ...]:
        """Select candidate pairs and compare them in one LLM call."""

        if len(evidence) < 2:
            return ()

        pairs = self._select_pairs(evidence)

        if not pairs:
            return ()

        logger.info(
            "Contradiction detection: %d candidate pair(s).",
            len(pairs),
        )

        return self._batch_compare(pairs)

    def _select_pairs(
        self,
        evidence: tuple[AnalysisEvidence, ...],
    ) -> list[tuple[AnalysisEvidence, AnalysisEvidence]]:
        """Select a small deterministic set of evidence pairs."""

        pairs: list[tuple[AnalysisEvidence, AnalysisEvidence]] = []

        if len(evidence) <= 4:
            for index, evidence_a in enumerate(evidence):
                for evidence_b in evidence[index + 1:]:
                    if self._should_skip_pair(
                        evidence_a,
                        evidence_b,
                    ):
                        continue

                    pairs.append((evidence_a, evidence_b))

                    if len(pairs) >= self.MAX_COMPARISONS:
                        return pairs

            return pairs

        for index in range(len(evidence) - 1):
            if len(pairs) >= self.MAX_COMPARISONS:
                break

            evidence_a = evidence[index]
            evidence_b = evidence[index + 1]

            if self._should_skip_pair(
                evidence_a,
                evidence_b,
            ):
                logger.debug(
                    "Skipping non-comparable evidence pair: %s vs %s",
                    evidence_a.evidence_id,
                    evidence_b.evidence_id,
                )
                continue

            if self._potentially_comparable(
                evidence_a,
                evidence_b,
            ):
                pairs.append((evidence_a, evidence_b))

        strongest = evidence[0]

        for item in evidence[2:]:
            if len(pairs) >= self.MAX_COMPARISONS:
                break

            pair = (strongest, item)

            if pair in pairs:
                continue

            if self._should_skip_pair(
                strongest,
                item,
            ):
                logger.debug(
                    "Skipping non-comparable evidence pair: %s vs %s",
                    strongest.evidence_id,
                    item.evidence_id,
                )
                continue

            if self._potentially_comparable(
                strongest,
                item,
            ):
                pairs.append(pair)

        if not pairs and len(evidence) >= 2:
            first = evidence[0]
            second = evidence[1]

            if not self._should_skip_pair(
                first,
                second,
            ):
                pairs.append((first, second))

        return pairs[: self.MAX_COMPARISONS]

    @classmethod
    def _should_skip_pair(
        cls,
        evidence_a: AnalysisEvidence,
        evidence_b: AnalysisEvidence,
    ) -> bool:
        """Identify evidence pairs that should not be compared."""

        if cls._is_different_year_ucdp_dyadic_pair(
            evidence_a,
            evidence_b,
        ):
            return True

        if cls._is_different_ucdp_ged_event_pair(
            evidence_a,
            evidence_b,
        ):
            return True

        return cls._is_different_acled_event_pair(
            evidence_a,
            evidence_b,
        )

    @classmethod
    def _is_different_year_ucdp_dyadic_pair(
        cls,
        evidence_a: AnalysisEvidence,
        evidence_b: AnalysisEvidence,
    ) -> bool:
        """Return True for the same UCDP dyad represented by different years."""

        source_a = str(evidence_a.source).strip().casefold()
        source_b = str(evidence_b.source).strip().casefold()

        if source_a != "ucdp dyadic" or source_b != "ucdp dyadic":
            return False

        match_a = cls._UCDP_DYADIC_ID_PATTERN.match(
            str(evidence_a.evidence_id).strip()
        )
        match_b = cls._UCDP_DYADIC_ID_PATTERN.match(
            str(evidence_b.evidence_id).strip()
        )

        if match_a is None or match_b is None:
            return False

        dyad_a = match_a.group("dyad")
        dyad_b = match_b.group("dyad")
        year_a = match_a.group("year")
        year_b = match_b.group("year")

        if dyad_a != dyad_b:
            return False

        if year_a == year_b:
            return False

        logger.info(
            "UCDP annual-record pair identified as non-comparable: "
            "%s (%s) vs %s (%s).",
            evidence_a.evidence_id,
            year_a,
            evidence_b.evidence_id,
            year_b,
        )

        return True

    @classmethod
    def _is_different_ucdp_ged_event_pair(
        cls,
        evidence_a: AnalysisEvidence,
        evidence_b: AnalysisEvidence,
    ) -> bool:
        """Return True when UCDP GED records refer to different events."""

        source_a = str(evidence_a.source).strip().casefold()
        source_b = str(evidence_b.source).strip().casefold()

        if source_a != "ucdp ged" or source_b != "ucdp ged":
            return False

        match_a = cls._UCDP_GED_ID_PATTERN.match(
            str(evidence_a.evidence_id).strip()
        )
        match_b = cls._UCDP_GED_ID_PATTERN.match(
            str(evidence_b.evidence_id).strip()
        )

        if match_a is None or match_b is None:
            return False

        event_a = match_a.group("event_id")
        event_b = match_b.group("event_id")

        if event_a == event_b:
            return False

        logger.info(
            "UCDP GED records identified as distinct events: "
            "%s vs %s.",
            evidence_a.evidence_id,
            evidence_b.evidence_id,
        )

        return True

    @classmethod
    def _is_different_acled_event_pair(
        cls,
        evidence_a: AnalysisEvidence,
        evidence_b: AnalysisEvidence,
    ) -> bool:
        """Return True when ACLED records refer to different events."""

        source_a = str(evidence_a.source).strip().casefold()
        source_b = str(evidence_b.source).strip().casefold()

        if source_a != "acled" or source_b != "acled":
            return False

        match_a = cls._ACLED_ID_PATTERN.match(
            str(evidence_a.evidence_id).strip()
        )
        match_b = cls._ACLED_ID_PATTERN.match(
            str(evidence_b.evidence_id).strip()
        )

        if match_a is None or match_b is None:
            return False

        event_a = match_a.group("event_id")
        event_b = match_b.group("event_id")

        if event_a == event_b:
            return False

        logger.info(
            "ACLED records identified as distinct events: "
            "%s vs %s.",
            evidence_a.evidence_id,
            evidence_b.evidence_id,
        )

        return True

    @classmethod
    def _potentially_comparable(
        cls,
        evidence_a: AnalysisEvidence,
        evidence_b: AnalysisEvidence,
    ) -> bool:
        """Cheaply identify evidence pairs worth comparing."""

        text_a = cls._normalise(
            " ".join(
                [
                    str(evidence_a.title),
                    str(evidence_a.text),
                ]
            )
        )

        text_b = cls._normalise(
            " ".join(
                [
                    str(evidence_b.title),
                    str(evidence_b.text),
                ]
            )
        )

        tokens_a = cls._tokenize(text_a)
        tokens_b = cls._tokenize(text_b)

        if not tokens_a or not tokens_b:
            return False

        overlap = len(tokens_a & tokens_b) / min(
            len(tokens_a),
            len(tokens_b),
        )

        if overlap >= 0.08:
            return True

        factual_a = cls._factual_terms(text_a)
        factual_b = cls._factual_terms(text_b)

        if factual_a & factual_b:
            return True

        numbers_a = cls._numbers(text_a)
        numbers_b = cls._numbers(text_b)

        return bool(numbers_a & numbers_b)

    def _batch_compare(
        self,
        pairs: list[tuple[AnalysisEvidence, AnalysisEvidence]],
    ) -> tuple[ContradictionResult, ...]:
        """Compare all selected pairs using one structured LLM call."""

        system_prompt = (
            "You are an evidence consistency analyst for MIL-EVID.\n\n"
            "You will receive multiple evidence pairs.\n"
            "For EACH pair, determine whether the two supplied evidence "
            "items support each other, contradict each other, or cannot "
            "be meaningfully compared.\n\n"
            "Use ONLY the supplied evidence.\n"
            "Do NOT use general world knowledge.\n"
            "Do NOT infer missing facts.\n"
            "Do NOT assume either evidence item is correct.\n\n"

            "A contradiction requires incompatible claims about the same "
            "or directly comparable subject.\n"
            "Differences in wording are NOT contradictions.\n"
            "Different locations, dates, events, or casualty counts are "
            "NOT contradictions unless the evidence describes the same "
            "comparable factual proposition.\n"
            "A temporal difference is a contradiction only when the "
            "evidence describes incompatible states for the same "
            "time-sensitive fact.\n\n"

            "IMPORTANT UCDP DYADIC RULE:\n"
            "UCDP Dyadic records may represent the same dyad in different "
            "annual records. A difference between annual record years is "
            "NOT by itself a contradiction. Do not classify annual UCDP "
            "records as contradictory merely because one record is from "
            "2023 and another is from 2025.\n\n"

            "IMPORTANT UCDP GED RULE:\n"
            "UCDP GED records identify individual conflict events. "
            "Different UCDP GED event IDs represent different event "
            "records. Do not classify two different GED event IDs as "
            "the same event merely because they have similar actors, "
            "locations, wording, or casualty information. Differences "
            "between distinct GED event records are NOT by themselves "
            "contradictions.\n\n"

            "IMPORTANT ACLED RULE:\n"
            "ACLED records identify individual conflict events. "
            "Different ACLED event IDs represent different event "
            "records. Do not classify two different ACLED event IDs as "
            "the same event merely because they have similar actors, "
            "locations, wording, or casualty information. Differences "
            "between distinct ACLED event records are NOT by themselves "
            "contradictions.\n\n"

            "IMPORTANT CROSS-SOURCE RULE:\n"
            "UCDP GED and ACLED are independent event databases. "
            "Do not treat two records as the same event merely because "
            "they share actors, locations, wording, event types, or "
            "casualty information. Different dates are NOT by themselves "
            "a contradiction. Only classify a contradiction when the "
            "evidence directly supports incompatible factual claims about "
            "the same identifiable event or directly comparable fact.\n\n"

            "Return exactly one result for every supplied pair.\n"
            "pair_index must match the supplied pair number.\n\n"

            "status must be exactly one of:\n"
            "ENTAILMENT, CONTRADICTION, NEUTRAL\n\n"

            "contradiction_type must be exactly one of:\n"
            "FACTUAL, TEMPORAL, UNCERTAIN, NONE\n\n"

            "score must be a number from 0.0 to 1.0.\n"
            "explanation must be short and based only on the evidence.\n"
        )

        pair_sections: list[str] = []

        for index, (evidence_a, evidence_b) in enumerate(
            pairs,
            start=1,
        ):
            pair_sections.append(
                "\n".join(
                    [
                        f"PAIR {index}",
                        "",
                        "EVIDENCE A",
                        f"ID: {evidence_a.evidence_id}",
                        f"Source: {evidence_a.source}",
                        f"Title: {evidence_a.title}",
                        f"Date: {evidence_a.date}",
                        f"Text: {evidence_a.text[:1500]}",
                        "",
                        "EVIDENCE B",
                        f"ID: {evidence_b.evidence_id}",
                        f"Source: {evidence_b.source}",
                        f"Title: {evidence_b.title}",
                        f"Date: {evidence_b.date}",
                        # f"Text: {evidence_b.text}",
                        f"Text: {evidence_b.text[:1500]}",
                    ]
                )
            )

        user_prompt = (
            "Analyze the following evidence pairs.\n\n"
            + "\n\n".join(pair_sections)
            + "\n\n"
            "Return one result for every pair."
        )

        schema = {
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "pair_index": {
                                "type": "integer",
                                "minimum": 1,
                            },
                            "status": {
                                "type": "string",
                                "enum": [
                                    "ENTAILMENT",
                                    "CONTRADICTION",
                                    "NEUTRAL",
                                ],
                            },
                            "contradiction_type": {
                                "type": "string",
                                "enum": [
                                    "FACTUAL",
                                    "TEMPORAL",
                                    "UNCERTAIN",
                                    "NONE",
                                ],
                            },
                            "score": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                            },
                            "explanation": {
                                "type": "string",
                            },
                        },
                        "required": [
                            "pair_index",
                            "status",
                            "contradiction_type",
                            "score",
                            "explanation",
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
                "Batch contradiction detection failed."
            )

            return self._fallback_results(pairs)

        return self._normalize_batch_response(
            response=response,
            pairs=pairs,
        )

    def _normalize_batch_response(
        self,
        *,
        response: dict,
        pairs: list[tuple[AnalysisEvidence, AnalysisEvidence]],
    ) -> tuple[ContradictionResult, ...]:
        """Validate, correct, and convert the batch response."""

        raw_results = response.get("results", [])

        if not isinstance(raw_results, list):
            logger.warning(
                "Contradiction LLM returned an invalid results list."
            )

            return self._fallback_results(pairs)

        results_by_index: dict[int, dict] = {}

        for item in raw_results:
            if not isinstance(item, dict):
                continue

            try:
                pair_index = int(item["pair_index"])
            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                continue

            if 1 <= pair_index <= len(pairs):
                results_by_index[pair_index] = item

        results: list[ContradictionResult] = []

        for pair_index, (evidence_a, evidence_b) in enumerate(
            pairs,
            start=1,
        ):
            # Deterministic guard takes precedence over the LLM.
            #
            # This prevents an LLM classification such as:
            #   different UCDP Dyadic annual records
            #   -> CONTRADICTION
            #
            # or:
            #   different UCDP GED/ACLED event records
            #   -> CONTRADICTION
            #
            # from becoming a false contradiction.
            if self._should_skip_pair(
                evidence_a,
                evidence_b,
            ):
                results.append(
                    self._non_comparable_pair_result(
                        evidence_a,
                        evidence_b,
                    )
                )
                continue

            item = results_by_index.get(pair_index)

            if item is None:
                results.append(
                    self._fallback_pair_result(
                        evidence_a,
                        evidence_b,
                    )
                )
                continue

            parsed = self._parse_structured_result(item)

            if parsed is None:
                results.append(
                    self._fallback_pair_result(
                        evidence_a,
                        evidence_b,
                    )
                )
                continue

            results.append(
                ContradictionResult(
                    evidence_a_id=evidence_a.evidence_id,
                    evidence_b_id=evidence_b.evidence_id,
                    status=parsed["status"],
                    contradiction_type=parsed["contradiction_type"],
                    score=parsed["score"],
                    explanation=parsed["explanation"],
                )
            )

        logger.info(
            "Contradiction detection completed: %d result(s).",
            len(results),
        )

        return tuple(results)

    @staticmethod
    def _non_comparable_pair_result(
        evidence_a: AnalysisEvidence,
        evidence_b: AnalysisEvidence,
    ) -> ContradictionResult:
        """Return a neutral result for a known non-comparable pair."""

        source_a = str(evidence_a.source).strip().casefold()
        source_b = str(evidence_b.source).strip().casefold()

        if source_a == "ucdp dyadic" and source_b == "ucdp dyadic":
            explanation = (
                "These UCDP Dyadic records represent different annual "
                "records for the same dyad; a difference in record year "
                "does not by itself establish a contradiction."
            )
        elif source_a == "ucdp ged" and source_b == "ucdp ged":
            explanation = (
                "These UCDP GED records represent distinct conflict "
                "events; differences between separate event records "
                "do not by themselves establish a contradiction."
            )
        elif source_a == "acled" and source_b == "acled":
            explanation = (
                "These ACLED records represent distinct events; "
                "differences between separate event records do not "
                "by themselves establish a contradiction."
            )
        else:
            explanation = (
                "These evidence items are not comparable under the "
                "deterministic consistency rules."
            )

        return ContradictionResult(
            evidence_a_id=evidence_a.evidence_id,
            evidence_b_id=evidence_b.evidence_id,
            status=ContradictionStatus.NEUTRAL,
            contradiction_type=ContradictionType.UNCERTAIN,
            score=0.0,
            explanation=explanation,
        )

    @staticmethod
    def _parse_structured_result(
        data: dict,
    ) -> dict | None:
        """Validate one contradiction result."""

        try:
            status = ContradictionStatus(
                str(data["status"]).strip().lower()
            )

            contradiction_type = ContradictionType(
                str(data["contradiction_type"]).strip().lower()
            )

            score = float(data["score"])
            explanation = str(data["explanation"]).strip()

        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            return None

        if not 0.0 <= score <= 1.0:
            return None

        if not explanation:
            explanation = "No explanation provided."

        return {
            "status": status,
            "contradiction_type": contradiction_type,
            "score": score,
            "explanation": explanation,
        }

    def _fallback_results(
        self,
        pairs: list[tuple[AnalysisEvidence, AnalysisEvidence]],
    ) -> tuple[ContradictionResult, ...]:
        """Return safe neutral results if the LLM call fails."""

        return tuple(
            self._fallback_pair_result(
                evidence_a,
                evidence_b,
            )
            for evidence_a, evidence_b in pairs
        )

    @staticmethod
    def _fallback_pair_result(
        evidence_a: AnalysisEvidence,
        evidence_b: AnalysisEvidence,
    ) -> ContradictionResult:
        """Create a conservative neutral result."""

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

    @staticmethod
    def _normalise(text: str) -> str:
        """Normalize text for lexical comparison."""

        return " ".join(text.lower().split())

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
    def _numbers(text: str) -> set[str]:
        """Extract numeric values."""

        return set(
            re.findall(
                r"\b\d+(?:\.\d+)?\b",
                text,
            )
        )

    @staticmethod
    def _factual_terms(text: str) -> set[str]:
        """Extract important military/conflict terms."""

        important_terms = {
            "civilian", "civilians", "residential", "infrastructure", "attack", "attacks", 
            "fatality", "fatalities", "killed", "injured", "government", "military", "forces", 
            "artillery", "shelling", "airstrike", "missile", "drone", "conflict", "escalation", 
            "damage", "destroyed", "death", "deaths","ukraine", "russia", "india", "pakistan", 
            "israel", "palestine", "china", "united kingdom", "united states", "france", "germany", 
            "colombia", "afghanistan"
        }

        return {
            term
            for term in important_terms
            if re.search(
                rf"\b{re.escape(term)}\b",
                text,
            )
        }

    @staticmethod
    def _parse_response(
        response: str,
    ) -> dict | None:
        """Parse a legacy single-result JSON response."""

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

            parsed = ContradictionDetector._parse_structured_result(
                data
            )

            if parsed is not None:
                return parsed

        return None