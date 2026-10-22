"""Tests for the shared Gemini client configuration (no network)."""

from app.config import settings
from app.gemini import (
    RETRY_ATTEMPTS,
    RETRYABLE_STATUSES,
    build_retry_options,
    get_client,
)


def test_retry_options_cover_only_transient_statuses():
    options = build_retry_options()
    assert options.attempts == RETRY_ATTEMPTS
    assert set(options.http_status_codes) == {429, 503}
    assert set(options.http_status_codes) == set(RETRYABLE_STATUSES)


def test_client_is_created_with_retry_options(monkeypatch):
    get_client.cache_clear()
    monkeypatch.setattr(settings, "gemini_api_key", "dummy-key-not-real")
    try:
        client = get_client()
        configured = client._api_client._http_options.retry_options
        assert configured is not None
        assert configured.attempts == RETRY_ATTEMPTS
    finally:
        get_client.cache_clear()
