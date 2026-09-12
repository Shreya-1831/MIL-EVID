import numpy as np
import pytest

from app.modules.retrieval import embedding_model


class FakeModel:
    def __init__(self, dimension: int = 3):
        self.dimension = dimension
        self.encode_calls = []

    def get_sentence_embedding_dimension(self):
        return self.dimension

    def encode(self, texts, **kwargs):
        self.encode_calls.append(
            {
                "texts": texts,
                **kwargs,
            }
        )

        return np.ones(
            (len(texts), self.dimension),
            dtype=np.float32,
        )


def test_get_embedding_model_caches_by_name(monkeypatch):
    calls = []

    class FakeSentenceTransformer:
        def __init__(self, model_name, device=None):
            calls.append(model_name)

    monkeypatch.setattr(
        embedding_model,
        "SentenceTransformer",
        FakeSentenceTransformer,
    )

    embedding_model.get_embedding_model.cache_clear()

    model_a = embedding_model.get_embedding_model(
        "test-model"
    )
    model_b = embedding_model.get_embedding_model(
        "test-model"
    )

    assert model_a is model_b
    assert calls == ["test-model"]

    embedding_model.get_embedding_model.cache_clear()


def test_get_embedding_model_rejects_empty_name():
    embedding_model.get_embedding_model.cache_clear()

    with pytest.raises(ValueError, match="non-empty"):
        embedding_model.get_embedding_model("")


def test_get_embedding_model_rejects_whitespace_name():
    embedding_model.get_embedding_model.cache_clear()

    with pytest.raises(ValueError, match="non-empty"):
        embedding_model.get_embedding_model("   ")


def test_embed_empty_texts_returns_empty_matrix():
    model = FakeModel(dimension=3)

    result = embedding_model.embed_texts(
        [],
        model=model,
    )

    assert result.shape == (0, 3)
    assert result.dtype == np.float32
    assert model.encode_calls == []


def test_embed_texts_returns_float32_matrix():
    model = FakeModel(dimension=3)

    result = embedding_model.embed_texts(
        ["first text", "second text"],
        model=model,
    )

    assert result.shape == (2, 3)
    assert result.dtype == np.float32


def test_embed_texts_passes_expected_encode_options():
    model = FakeModel(dimension=3)

    embedding_model.embed_texts(
        ["hello", "world"],
        model=model,
        batch_size=16,
        show_progress_bar=True,
    )

    call = model.encode_calls[0]

    assert call["texts"] == ["hello", "world"]
    assert call["batch_size"] == 16
    assert call["show_progress_bar"] is True
    assert call["convert_to_numpy"] is True
    assert call["normalize_embeddings"] is True


@pytest.mark.parametrize("batch_size", [0, -1, -10])
def test_embed_texts_rejects_invalid_batch_size(batch_size):
    model = FakeModel()

    with pytest.raises(
        ValueError,
        match="batch_size must be greater than 0",
    ):
        embedding_model.embed_texts(
            ["hello"],
            model=model,
            batch_size=batch_size,
        )


def test_embed_texts_rejects_non_string_values():
    model = FakeModel()

    with pytest.raises(
        ValueError,
        match="all texts must be strings",
    ):
        embedding_model.embed_texts(
            ["valid text", 123],
            model=model,
        )


def test_embed_texts_rejects_non_2d_output():
    class InvalidModel(FakeModel):
        def encode(self, texts, **kwargs):
            return np.ones(3, dtype=np.float32)

    model = InvalidModel()

    with pytest.raises(
        ValueError,
        match="2-D embedding matrix",
    ):
        embedding_model.embed_texts(
            ["hello"],
            model=model,
        )


def test_embed_texts_rejects_wrong_number_of_embeddings():
    class InvalidModel(FakeModel):
        def encode(self, texts, **kwargs):
            return np.ones(
                (1, self.dimension),
                dtype=np.float32,
            )

    model = InvalidModel()

    with pytest.raises(
        ValueError,
        match="unexpected number of embeddings",
    ):
        embedding_model.embed_texts(
            ["first", "second"],
            model=model,
        )


def test_embed_texts_rejects_wrong_embedding_dimension():
    class InvalidModel(FakeModel):
        def encode(self, texts, **kwargs):
            return np.ones(
                (len(texts), 5),
                dtype=np.float32,
            )

    model = InvalidModel(dimension=3)

    with pytest.raises(
        ValueError,
        match="unexpected embedding dimension",
    ):
        embedding_model.embed_texts(
            ["hello"],
            model=model,
        )


def test_embed_texts_rejects_nan_values():
    class InvalidModel(FakeModel):
        def encode(self, texts, **kwargs):
            result = np.ones(
                (len(texts), self.dimension),
                dtype=np.float32,
            )
            result[0, 0] = np.nan
            return result

    model = InvalidModel()

    with pytest.raises(
        ValueError,
        match="NaN or Inf",
    ):
        embedding_model.embed_texts(
            ["hello"],
            model=model,
        )


def test_embed_texts_rejects_inf_values():
    class InvalidModel(FakeModel):
        def encode(self, texts, **kwargs):
            result = np.ones(
                (len(texts), self.dimension),
                dtype=np.float32,
            )
            result[0, 0] = np.inf
            return result

    model = InvalidModel()

    with pytest.raises(
        ValueError,
        match="NaN or Inf",
    ):
        embedding_model.embed_texts(
            ["hello"],
            model=model,
        )


def test_embedding_dimension():
    model = FakeModel(dimension=384)

    assert embedding_model.embedding_dimension(model) == 384


def test_embedding_dimension_rejects_invalid_dimension():
    model = FakeModel(dimension=0)

    with pytest.raises(
        ValueError,
        match="invalid embedding dimension",
    ):
        embedding_model.embedding_dimension(model)