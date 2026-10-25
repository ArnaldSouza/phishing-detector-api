"""Shared Gemini client and API error translation."""

from functools import lru_cache
from typing import Final

import httpx
from google import genai
from google.genai import errors, types

from app.config import settings

RATE_LIMIT_STATUS: Final[int] = 429
UNAVAILABLE_STATUS: Final[int] = 503
SERVER_ERROR_MIN_STATUS: Final[int] = 500

# Total tries, including the first one. Kept low so a request never hangs long.
RETRY_ATTEMPTS: Final[int] = 3
RETRY_INITIAL_DELAY_SECONDS: Final[float] = 2.0
RETRY_MAX_DELAY_SECONDS: Final[float] = 10.0
RETRYABLE_STATUSES: Final[tuple[int, ...]] = (RATE_LIMIT_STATUS, UNAVAILABLE_STATUS)

# Per attempt, in milliseconds (the SDK unit). Stops a stalled call from
# holding a database connection while the request waits for Gemini.
REQUEST_TIMEOUT_MS: Final[int] = 30_000

class GeminiError(RuntimeError):
    """Base class for failures when talking to the Gemini API.

    Attributes:
        status_code: HTTP status returned by Gemini, or None when the failure
            happened before any request (for example, a missing API key).
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def build_retry_options() -> types.HttpRetryOptions:
    """Retry only transient statuses, with a short exponential backoff.

    The SDK does not retry unless it is given these options.
    """
    return types.HttpRetryOptions(
        attempts=RETRY_ATTEMPTS,
        initial_delay=RETRY_INITIAL_DELAY_SECONDS,
        max_delay=RETRY_MAX_DELAY_SECONDS,
        http_status_codes=list(RETRYABLE_STATUSES),
    )


@lru_cache(maxsize=1)
def get_client() -> genai.Client:
    """Create the Gemini client once, failing clearly if the key is missing."""
    if not settings.gemini_api_key:
        raise GeminiError("GEMINI_API_KEY is not set. Add it to your .env file.")
    return genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(
            timeout=REQUEST_TIMEOUT_MS,
            retry_options=build_retry_options(),
        ),
    )


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


def describe_network_error(error: httpx.HTTPError) -> str:
    """Turn a network failure (timeout, connection) into a clear message."""
    if isinstance(error, httpx.TimeoutException):
        return "Gemini did not answer in time. Try again shortly."
    return "Could not reach Gemini. Try again shortly."