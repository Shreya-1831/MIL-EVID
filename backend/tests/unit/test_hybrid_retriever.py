from unittest.mock import Mock

import pytest

from app.modules.retrieval.bm25_index import BM25SearchResult
from app.modules.retrieval.faiss_index import DenseSearchResult
from app.modules.retrieval.hybrid_retriever import HybridRetriever


def make_retriever():
    bm25 = Mock()
    faiss = Mock()

    return (
        HybridRetriever(
            bm25_index=bm25,
            faiss_index=faiss,
        ),
        bm25,
        faiss,
    )


def test_empty_query_returns_empty():
    retriever, bm25, faiss = make_retriever()

    result = retriever.search(
        "   ",
        top_k=5,
    )

    assert result == []
    bm25.search.assert_not_called()
    faiss.search.assert_not_called()


def test_top_k_zero_returns_empty():
    retriever, bm25, faiss = make_retriever()

    result = retriever.search(
        "military conflict",
        top_k=0,
    )

    assert result == []
    bm25.search.assert_not_called()
    faiss.search.assert_not_called()


def test_hybrid_search_calls_both_retrievers():
    retriever, bm25, faiss = make_retriever()

    bm25.search.return_value = [
        BM25SearchResult(
            chunk_id="a",
            score=10.0,
        ),
    ]

    faiss.search.return_value = [
        DenseSearchResult(
            chunk_id="b",
            score=0.8,
        ),
    ]

    results = retriever.search(
        "military conflict",
        top_k=2,
    )

    bm25.search.assert_called_once_with(
        "military conflict",
        top_k=2,
    )

    faiss.search.assert_called_once_with(
        "military conflict",
        top_k=2,
    )

    assert len(results) == 2


def test_hybrid_favors_chunk_present_in_both():
    retriever, bm25, faiss = make_retriever()

    bm25.search.return_value = [
        BM25SearchResult("a", 10.0),
        BM25SearchResult("b", 5.0),
    ]

    faiss.search.return_value = [
        DenseSearchResult("b", 0.9),
        DenseSearchResult("c", 0.8),
    ]

    results = retriever.search(
        "civilian protection",
        top_k=3,
    )

    assert results[0].chunk_id == "b"


def test_custom_retrieval_depths():
    retriever, bm25, faiss = make_retriever()

    bm25.search.return_value = []
    faiss.search.return_value = []

    retriever.search(
        "conflict",
        top_k=5,
        bm25_top_k=20,
        dense_top_k=30,
    )

    bm25.search.assert_called_once_with(
        "conflict",
        top_k=20,
    )

    faiss.search.assert_called_once_with(
        "conflict",
        top_k=30,
    )


def test_invalid_bm25_depth():
    retriever, _, _ = make_retriever()

    with pytest.raises(ValueError):
        retriever.search(
            "conflict",
            bm25_top_k=0,
        )


def test_invalid_dense_depth():
    retriever, _, _ = make_retriever()

    with pytest.raises(ValueError):
        retriever.search(
            "conflict",
            dense_top_k=0,
        )