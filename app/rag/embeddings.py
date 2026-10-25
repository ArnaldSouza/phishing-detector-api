"""Generate normalized text embeddings with the Gemini API."""

import math
from typing import Final

import httpx
from google.genai import errors, types

from app.config import settings
from app.gemini import (
    GeminiError,
    describe_api_error,
    describe_network_error,
    get_client,
)
from app.models import EMBEDDING_DIMENSION

DOCUMENT_TASK: Final[str] = "RETRIEVAL_DOCUMENT"
QUERY_TASK: Final[str] = "RETRIEVAL_QUERY"


class EmbeddingError(GeminiError):
    """Raised when embeddings cannot be generated."""


def normalize(vector: list[float]) -> list[float]:
    """Scale a vector to unit length.

    Truncated Gemini embeddings are not normalized, and cosine search gives
    misleading rankings with vectors of different lengths.
    """
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        raise EmbeddingError("Cannot normalize a zero vector")
    return [value / norm for value in vector]

def _vector_of(item: types.ContentEmbedding) -> list[float]:
    """Return the raw values of one embedding, or raise if the API sent none."""
    if not item.values:
        raise EmbeddingError("Gemini returned an embedding without values.")
    return list(item.values)

def embed_texts(texts: list[str], task_type: str) -> list[list[float]]:
    """Embed several texts in a single API request.

    Args:
        texts: Texts to embed.
        task_type: ``DOCUMENT_TASK`` for stored cases, ``QUERY_TASK`` for
            the text being searched.

    Returns:
        One normalized vector per input text, in the same order.

    Raises:
        GeminiError: If the API key is missing.
        EmbeddingError: If the request fails (including the free-tier
            limit) or the API returns something unexpected.
    """
    if not texts:
        return []

    try:
        response = get_client().models.embed_content(
            model=settings.gemini_embedding_model,
            contents=texts,
            config=types.EmbedContentConfig(
                output_dimensionality=EMBEDDING_DIMENSION,
                task_type=task_type,
            ),
        )
    except errors.APIError as error:
        raise EmbeddingError(
            describe_api_error(error, "embedding"), status_code=error.code
        ) from error
    except httpx.HTTPError as error:
        raise EmbeddingError(describe_network_error(error)) from error
    
    embeddings = response.embeddings or []
    if len(embeddings) != len(texts):
        raise EmbeddingError(
            f"Expected {len(texts)} embeddings, received {len(embeddings)}"
        )
    return [normalize(_vector_of(item)) for item in embeddings]
