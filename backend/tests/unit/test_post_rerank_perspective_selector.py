from datetime import datetime

from app.domain.enums import Perspective, SourceType
from app.domain.models.analysis import AnalysisEvidence
from app.modules.analysis.post_rerank_perspective_selector import (
    PostRerankPerspectiveSelector,
)


def make_evidence(
    evidence_id: str,
    perspective: Perspective,
    score: float,
    text: str | None = None,
    source: str = "test",
) -> AnalysisEvidence:
    return AnalysisEvidence(
        evidence_id=evidence_id,
        text=text or f"Evidence {evidence_id}",
        source=source,
        source_type=SourceType.UCDP,
        perspective=perspective,
        title=evidence_id,
        date=datetime(2025, 1, 1),
        reranker_score=score,
        original_rrf_score=0.1,
        ranks=(1,),
    )


def test_selects_up_to_five_evidence_items_per_source() -> None:
    selector = PostRerankPerspectiveSelector()

    evidence = (
        make_evidence("military-1", Perspective.MILITARY, 0.99, source="military"),
        make_evidence("military-2", Perspective.MILITARY, 0.98, source="military"),
        make_evidence("military-3", Perspective.MILITARY, 0.97, source="military"),
        make_evidence("military-4", Perspective.MILITARY, 0.96, source="military"),
        make_evidence("military-5", Perspective.MILITARY, 0.95, source="military"),
        make_evidence("military-6", Perspective.MILITARY, 0.94, source="military"),
        make_evidence("legal-1", Perspective.LEGAL, 0.50, source="legal"),
        make_evidence("legal-2", Perspective.LEGAL, 0.49, source="legal"),
        make_evidence("historical-1", Perspective.HISTORICAL, 0.40, source="historical"),
    )

    result = selector.select(
        query="Assess military, legal, and historical perspectives.",
        evidence=evidence,
        max_evidence=20,
    )

    selected_ids = [item.evidence_id for item in result]

    assert len(result) == 8

    assert selected_ids == [
        "military-1",
        "legal-1",
        "historical-1",
        "military-2",
        "legal-2",
        "military-3",
        "military-4",
        "military-5",
    ]

    assert "military-6" not in selected_ids


def test_respects_final_evidence_budget() -> None:
    selector = PostRerankPerspectiveSelector()

    evidence = (
        make_evidence("military-1", Perspective.MILITARY, 0.99, source="military"),
        make_evidence("military-2", Perspective.MILITARY, 0.98, source="military"),
        make_evidence("military-3", Perspective.MILITARY, 0.97, source="military"),
        make_evidence("military-4", Perspective.MILITARY, 0.96, source="military"),
        make_evidence("military-5", Perspective.MILITARY, 0.95, source="military"),
        make_evidence("legal-1", Perspective.LEGAL, 0.90, source="legal"),
        make_evidence("legal-2", Perspective.LEGAL, 0.89, source="legal"),
    )

    result = selector.select(
        query="Assess military and legal developments.",
        evidence=evidence,
        max_evidence=5,
    )

    assert len(result) == 5
    assert [item.evidence_id for item in result] == [
        "military-1",
        "legal-1",
        "military-2",
        "legal-2",
        "military-3",
    ]


def test_does_not_duplicate_evidence() -> None:
    selector = PostRerankPerspectiveSelector()

    evidence = (
        make_evidence("military-1", Perspective.MILITARY, 0.99),
        make_evidence("legal-1", Perspective.LEGAL, 0.80),
        make_evidence("historical-1", Perspective.HISTORICAL, 0.70),
    )

    result = selector.select(
        query="military legal historical assessment",
        evidence=evidence,
        max_evidence=5,
    )

    ids = [item.evidence_id for item in result]

    assert len(ids) == len(set(ids))


def test_single_perspective_preserves_reranker_order() -> None:
    selector = PostRerankPerspectiveSelector()

    evidence = (
        make_evidence("military-1", Perspective.MILITARY, 0.99),
        make_evidence("military-2", Perspective.MILITARY, 0.80),
        make_evidence("military-3", Perspective.MILITARY, 0.70),
    )

    result = selector.select(
        query="What military attacks occurred?",
        evidence=evidence,
        max_evidence=2,
    )

    assert [item.evidence_id for item in result] == [
        "military-1",
        "military-2",
    ]


def test_allows_redundant_evidence_within_source() -> None:
    selector = PostRerankPerspectiveSelector()

    evidence = (
        make_evidence(
            "legal-1",
            Perspective.LEGAL,
            0.90,
            text="Civilians and civilian objects must be distinguished from military objectives during attacks.",
            source="legal",
        ),
        make_evidence(
            "legal-2",
            Perspective.LEGAL,
            0.85,
            text="Civilians and civilian objects must be distinguished from military objectives during attacks.",
            source="legal",
        ),
        make_evidence(
            "legal-3",
            Perspective.LEGAL,
            0.80,
            text="Proportionality prohibits attacks expected to cause excessive civilian harm compared with the anticipated military advantage.",
            source="legal",
        ),
    )

    result = selector.select(
        query="Assess civilian protection and proportionality.",
        evidence=evidence,
        max_evidence=2,
    )

    selected_ids = [item.evidence_id for item in result]

    assert selected_ids == ["legal-1", "legal-2"]


def test_does_not_reduce_available_evidence_below_source_limit() -> None:
    selector = PostRerankPerspectiveSelector()

    evidence = (
        make_evidence(
            "legal-1",
            Perspective.LEGAL,
            0.90,
            text="Civilians must be protected from attack.",
            source="legal",
        ),
        make_evidence(
            "legal-2",
            Perspective.LEGAL,
            0.80,
            text="Civilians must be protected from attack.",
            source="legal",
        ),
        make_evidence(
            "military-1",
            Perspective.MILITARY,
            0.70,
            text="Military forces exchanged artillery fire.",
            source="military",
        ),
        make_evidence(
            "historical-1",
            Perspective.HISTORICAL,
            0.60,
            text="The conflict continued during the previous year.",
            source="historical",
        ),
    )

    result = selector.select(
        query="Assess military and legal developments.",
        evidence=evidence,
        max_evidence=20,
    )

    assert len(result) == 4

    ids = [item.evidence_id for item in result]

    assert len(ids) == len(set(ids))
    assert ids == [
        "legal-1",
        "military-1",
        "historical-1",
        "legal-2",
    ]


def test_preserves_cross_encoder_order_after_source_selection() -> None:
    selector = PostRerankPerspectiveSelector()

    evidence = (
        make_evidence(
            "legal-1",
            Perspective.LEGAL,
            0.90,
            text="Civilians must be distinguished from combatants.",
            source="legal",
        ),
        make_evidence(
            "legal-2",
            Perspective.LEGAL,
            0.85,
            text="Civilians must be distinguished from combatants.",
            source="legal",
        ),
        make_evidence(
            "military-1",
            Perspective.MILITARY,
            0.80,
            text="Military forces exchanged artillery fire.",
            source="military",
        ),
        make_evidence(
            "historical-1",
            Perspective.HISTORICAL,
            0.70,
            text="The conflict continued during the previous year.",
            source="historical",
        ),
    )

    result = selector.select(
        query="Assess military, legal, and historical factors.",
        evidence=evidence,
        max_evidence=3,
    )

    scores = [item.reranker_score for item in result]

    assert scores == sorted(scores, reverse=True)