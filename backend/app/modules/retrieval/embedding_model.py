"""Sentence Transformer loading and batch embedding generation.

This module is responsible only for:
1. Loading and caching the configured Sentence Transformer model.
2. Converting text into normalized dense embedding vectors.

Persistence and FAISS indexing are handled separately by faiss_index.py.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer
import torch
from app.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_BATCH_SIZE = 64


# @lru_cache(maxsize=4)
# def get_embedding_model(model_name: str) -> SentenceTransformer:
#     """Load and cache a Sentence Transformer model by name.

#     The model is cached by model name so repeated indexing/retrieval
#     operations in the same process do not reload the model.
#     """
#     if not isinstance(model_name, str) or not model_name.strip():
#         raise ValueError("model_name must be a non-empty string")

#     logger.info(
#         "embedding_model_loading",
#         model_name=model_name,
#     )

#     return SentenceTransformer(model_name)

@lru_cache(maxsize=4)
def get_embedding_model(model_name: str) -> SentenceTransformer:
    """Load and cache a Sentence Transformer model by name."""
    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError("model_name must be a non-empty string")

    device = "cuda" if torch.cuda.is_available() else "cpu"

    logger.info(
        "embedding_model_loading",
        model_name=model_name,
        device=device,
    )

    return SentenceTransformer(
        model_name,
        device=device,
    )


def embed_texts(
    texts: Sequence[str],
    *,
    model: SentenceTransformer,
    batch_size: int = DEFAULT_BATCH_SIZE,
    show_progress_bar: bool = False,
) -> np.ndarray:
    """Encode texts into L2-normalized float32 embeddings.

    Args:
        texts: Texts to encode.
        model: Loaded Sentence Transformer model.
        batch_size: Number of texts processed by the model at once.
        show_progress_bar: Whether SentenceTransformer should display
            its progress bar.

    Returns:
        A 2-D NumPy array with shape:

            (number_of_texts, embedding_dimension)

        The vectors are float32 and normalized so that cosine
        similarity can later be implemented using FAISS inner product.

    Raises:
        ValueError:
            If batch_size is invalid, text input is invalid, or the
            model returns an invalid embedding matrix.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0")

    texts_list = list(texts)

    if any(not isinstance(text, str) for text in texts_list):
        raise ValueError("all texts must be strings")

    dimension = model.get_sentence_embedding_dimension()

    if dimension is None or dimension <= 0:
        raise ValueError(
            "model returned an invalid embedding dimension"
        )

    if not texts_list:
        return np.empty(
            (0, dimension),
            dtype=np.float32,
        )

    embeddings = model.encode(
        texts_list,
        batch_size=batch_size,
        show_progress_bar=show_progress_bar,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    embeddings = np.asarray(
        embeddings,
        dtype=np.float32,
    )

    # Validate dimensionality.
    if embeddings.ndim != 2:
        raise ValueError(
            "model must return a 2-D embedding matrix"
        )

    # Validate number of returned vectors.
    if embeddings.shape[0] != len(texts_list):
        raise ValueError(
            "model returned an unexpected number of embeddings: "
            f"expected {len(texts_list)}, "
            f"got {embeddings.shape[0]}"
        )

    # Validate embedding dimension.
    if embeddings.shape[1] != dimension:
        raise ValueError(
            "model returned an unexpected embedding dimension: "
            f"expected {dimension}, "
            f"got {embeddings.shape[1]}"
        )

    # FAISS cannot meaningfully work with NaN/Inf vectors.
    if not np.isfinite(embeddings).all():
        raise ValueError(
            "model returned embeddings containing NaN or Inf values"
        )

    return embeddings


def embedding_dimension(model: SentenceTransformer) -> int:
    """Return the output embedding dimensionality of a model."""
    dimension = model.get_sentence_embedding_dimension()

    if dimension is None or dimension <= 0:
        raise ValueError(
            "model returned an invalid embedding dimension"
        )

    return int(dimension)