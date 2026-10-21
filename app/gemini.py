"""Shared Gemini client and API error translation."""

from functools import lru_cache
from typing import Final

from google import genai
from google.genai import errors

from app.config import settings

RATE_LIMIT_STATUS: Final[int] = 429
SERVER_ERROR_MIN_STATUS: Final[int] = 500


class GeminiError(RuntimeError):
    """Base class for failures when talking to the Gemini API."""


@lru_cache(maxsize=1)
def get_client() -> genai.Client:
    """Create the Gemini client once, failing clearly if the key is missing."""
    if not settings.gemini_api_key:
        raise GeminiError("GEMINI_API_KEY is not set. Add it to your .env file.")
    return genai.Client(api_key=settings.gemini_api_key)


def describe_api_error(error: errors.APIError, action: str) -> str:
    """Turn a Gemini API error into a clear, user-facing message.

    Args:
        error: The error raised by the SDK.
        action: What was being done, e.g. ``"embedding"`` or ``"chat"``.
    """
    if error.code == RATE_LIMIT_STATUS:
        return "Gemini free-tier rate limit reached. Wait a minute and retry."
    if error.code is not None and error.code >= SERVER_ERROR_MIN_STATUS:
        return "Gemini is overloaded or unavailable. Try again shortly."
    return f"Gemini {action} request failed: {error}"
