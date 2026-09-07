from dataclasses import dataclass

import pytest

from app.modules.retrieval.rrf import (
    reciprocal_rank_fusion,
)


@dataclass(frozen=True)
class FakeResult:
    chunk_id: str
    score: float


def test_rrf_empty_lists():
    assert reciprocal_rank_fusion(
        [],
        top_k=5,
    ) == []


def test_rrf_top_k_zero():
    assert reciprocal_rank_fusion(
        [[FakeResult("a", 1.0)]],
        top_k=0,
    ) == []


def test_rrf_rejects_invalid_k():
    with pytest.raises(ValueError):
        reciprocal_rank_fusion(
            [],
            k=0,
        )


def test_rrf_single_result_list():
    results = reciprocal_rank_fusion(
        [
            [
                FakeResult("a", 10.0),
                FakeResult("b", 5.0),
                FakeResult("c", 1.0),
            ]
        ],
        top_k=3,
    )

    assert [result.chunk_id for result in results] == [
        "a",
        "b",
        "c",
    ]


def test_rrf_rewards_results_present_in_both_lists():
    results = reciprocal_rank_fusion(
        [
            [
                FakeResult("a", 10.0),
                FakeResult("b", 5.0),
            ],
            [
                FakeResult("b", 0.9),
                FakeResult("c", 0.8),
            ],
        ],
        top_k=3,
    )

    assert results[0].chunk_id == "b"

    assert results[0].score == pytest.approx(
        1 / 62 + 1 / 61
    )


def test_rrf_records_ranks():
    results = reciprocal_rank_fusion(
        [
            [
                FakeResult("a", 10.0),
                FakeResult("b", 5.0),
            ],
            [
                FakeResult("b", 0.9),
                FakeResult("a", 0.8),
            ],
        ],
        top_k=2,
    )

    by_id = {
        result.chunk_id: result
        for result in results
    }

    assert by_id["a"].ranks == (1, 2)
    assert by_id["b"].ranks == (2, 1)


def test_rrf_ignores_duplicate_chunk_within_same_list():
    results = reciprocal_rank_fusion(
        [
            [
                FakeResult("a", 10.0),
                FakeResult("a", 9.0),
                FakeResult("b", 5.0),
            ]
        ],
        top_k=5,
    )

    assert [result.chunk_id for result in results] == [
        "a",
        "b",
    ]


def test_rrf_deterministic_tie_breaking():
    results = reciprocal_rank_fusion(
        [
            [
                FakeResult("b", 1.0),
                FakeResult("a", 1.0),
            ]
        ],
        top_k=2,
    )

    assert [result.chunk_id for result in results] == [
        "b",
        "a",
    ]