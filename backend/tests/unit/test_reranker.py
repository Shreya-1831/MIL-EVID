from unittest.mock import Mock

import numpy as np
import pytest

from app.modules.retrieval.hybrid_retriever import HybridSearchResult
from app.modules.retrieval.reranker import (
    CrossEncoderReranker,
)


def candidate(
    chunk_id: str,
    rrf_score: float = 0.01,
    ranks: tuple[int, ...] = (1,),
) -> HybridSearchResult:
    return HybridSearchResult(
        chunk_id=chunk_id,
        score=rrf_score,
        ranks=ranks,
    )


def make_reranker(scores):
    model = Mock()

    model.predict.return_value = np.asarray(
        scores,
        dtype=np.float32,
    )

    reranker = CrossEncoderReranker(
        model_name="test-reranker",
        model=model,
    )

    return reranker, model


def test_empty_query_returns_empty():
    reranker, model = make_reranker([])

    result = reranker.rerank(
        query="   ",
        candidates=[
            candidate("a"),
        ],
        chunk_texts={
            "a": "some evidence",
        },
        top_k=5,
    )

    assert result == []
    model.predict.assert_not_called()


def test_empty_candidates_returns_empty():
    reranker, model = make_reranker([])

    result = reranker.rerank(
        query="military conflict",
        candidates=[],
        chunk_texts={},
        top_k=5,
    )

    assert result == []
    model.predict.assert_not_called()


def test_top_k_zero_returns_empty():
    reranker, model = make_reranker([])

    result = reranker.rerank(
        query="military conflict",
        candidates=[
            candidate("a"),
        ],
        chunk_texts={
            "a": "some evidence",
        },
        top_k=0,
    )

    assert result == []
    model.predict.assert_not_called()


def test_reranker_sends_query_and_text_pairs():
    reranker, model = make_reranker(
        [0.8, 0.4]
    )

    candidates = [
        candidate("a"),
        candidate("b"),
    ]

    reranker.rerank(
        query="civilian protection",
        candidates=candidates,
        chunk_texts={
            "a": "Evidence about civilians.",
            "b": "Evidence about military vehicles.",
        },
        top_k=2,
    )

    model.predict.assert_called_once()

    pairs = model.predict.call_args.args[0]

    assert pairs == [
        [
            "civilian protection",
            "Evidence about civilians.",
        ],
        [
            "civilian protection",
            "Evidence about military vehicles.",
        ],
    ]


def test_results_are_sorted_by_cross_encoder_score():
    reranker, _ = make_reranker(
        [0.2, 0.9, 0.5]
    )

    results = reranker.rerank(
        query="civilian protection",
        candidates=[
            candidate("a"),
            candidate("b"),
            candidate("c"),
        ],
        chunk_texts={
            "a": "text a",
            "b": "text b",
            "c": "text c",
        },
        top_k=3,
    )

    assert [result.chunk_id for result in results] == [
        "b",
        "c",
        "a",
    ]

    assert [result.score for result in results] == pytest.approx(
        [0.9, 0.5, 0.2]
    )


def test_original_rrf_information_is_preserved():
    reranker, _ = make_reranker([0.9])

    results = reranker.rerank(
        query="civilian protection",
        candidates=[
            candidate(
                "a",
                rrf_score=0.032266,
                ranks=(1, 3),
            ),
        ],
        chunk_texts={
            "a": "Relevant evidence.",
        },
        top_k=1,
    )

    assert results[0].chunk_id == "a"
    assert results[0].score == pytest.approx(0.9)
    assert results[0].original_rrf_score == pytest.approx(
        0.032266
    )
    assert results[0].ranks == (1, 3)


def test_missing_chunk_text_raises():
    reranker, _ = make_reranker([0.9])

    with pytest.raises(KeyError):
        reranker.rerank(
            query="civilian protection",
            candidates=[
                candidate("missing"),
            ],
            chunk_texts={},
            top_k=1,
        )


def test_blank_chunk_text_is_skipped():
    reranker, model = make_reranker([0.9])

    results = reranker.rerank(
        query="civilian protection",
        candidates=[
            candidate("a"),
            candidate("b"),
        ],
        chunk_texts={
            "a": "",
            "b": "Valid evidence.",
        },
        top_k=2,
    )

    assert len(results) == 1
    assert results[0].chunk_id == "b"

    pairs = model.predict.call_args.args[0]

    assert pairs == [
        [
            "civilian protection",
            "Valid evidence.",
        ]
    ]


def test_unexpected_score_count_raises():
    reranker, _ = make_reranker(
        [0.9]
    )

    with pytest.raises(ValueError):
        reranker.rerank(
            query="civilian protection",
            candidates=[
                candidate("a"),
                candidate("b"),
            ],
            chunk_texts={
                "a": "text a",
                "b": "text b",
            },
            top_k=2,
        )


def test_non_finite_score_raises():
    reranker, _ = make_reranker(
        [np.nan]
    )

    with pytest.raises(ValueError):
        reranker.rerank(
            query="civilian protection",
            candidates=[
                candidate("a"),
            ],
            chunk_texts={
                "a": "text a",
            },
            top_k=1,
        )


def test_tied_scores_are_deterministic():
    reranker, _ = make_reranker(
        [0.5, 0.5]
    )

    results = reranker.rerank(
        query="civilian protection",
        candidates=[
            candidate("b"),
            candidate("a"),
        ],
        chunk_texts={
            "a": "text a",
            "b": "text b",
        },
        top_k=2,
    )

    assert [result.chunk_id for result in results] == [
        "a",
        "b",
    ]