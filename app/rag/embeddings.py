"""Generate normalized text embeddings with the Gemini API."""

import math
from functools import lru_cache
from typing import Final

from google import genai
from google.genai import errors, types

from app.config import settings
from app.models import EMBEDDING_DIMENSION

DOCUMENT_TASK: Final[str] = "RETRIEVAL_DOCUMENT"
QUERY_TASK: Final[str] = "RETRIEVAL_QUERY"
RATE_LIMIT_STATUS: Final[int] = 429


class EmbeddingError(RuntimeError):
    """Raised when embeddings cannot be generated."""


@lru_cache(maxsize=1)
def _get_client() -> genai.Client:
    """Create the Gemini client once, failing clearly if the key is missing."""
    if not settings.gemini_api_key:
        raise EmbeddingError("GEMINI_API_KEY is not set. Add it to your .env file.")
    return genai.Client(api_key=settings.gemini_api_key)


def normalize(vector: list[float]) -> list[float]:
    """Scale a vector to unit length.

    Truncated Gemini embeddings are not normalized, and cosine search gives
    misleading rankings with vectors of different lengths.
    """
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        raise EmbeddingError("Cannot normalize a zero vector")
    return [value / norm for value in vector]


def embed_texts(texts: list[str], task_type: str) -> list[list[float]]:
    """Embed several texts in a single API request.

    Args:
        texts: Texts to embed.
        task_type: ``DOCUMENT_TASK`` for stored cases, ``QUERY_TASK`` for
            the text being searched.

    Returns:
        One normalized vector per input text, in the same order.

    Raises:
        EmbeddingError: If the key is missing, the free-tier limit is hit,
            or the API returns something unexpected.
    """
    if not texts:
        return []

    try:
        response = _get_client().models.embed_content(
            model=settings.gemini_embedding_model,
            contents=texts,
            config=types.EmbedContentConfig(
                output_dimensionality=EMBEDDING_DIMENSION,
                task_type=task_type,
            ),
        )
    except errors.APIError as error:
        if error.code == RATE_LIMIT_STATUS:
            raise EmbeddingError(
                "Gemini free-tier rate limit reached. Wait a minute and retry."
            ) from error
        raise EmbeddingError(f"Gemini embedding request failed: {error}") from error

    embeddings = response.embeddings or []
    if len(embeddings) != len(texts):
        raise EmbeddingError(
            f"Expected {len(texts)} embeddings, received {len(embeddings)}"
        )
    return [normalize(list(item.values)) for item in embeddings]