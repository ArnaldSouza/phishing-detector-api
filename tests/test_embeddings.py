"""Tests for text embeddings (Gemini is mocked, no network)."""

import math
from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors

from app.config import settings
from app.models import EMBEDDING_DIMENSION
from app.rag.embeddings import (
    DOCUMENT_TASK,
    QUERY_TASK,
    EmbeddingError,
    embed_texts,
    normalize,
)


class FakeModels:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def embed_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


def make_response(*vectors):
    return SimpleNamespace(
        embeddings=[SimpleNamespace(values=vector) for vector in vectors]
    )


def api_error_payload(code: int, status: str) -> dict:
    return {"error": {"code": code, "message": "test", "status": status}}


def install_fake(monkeypatch, response=None, error=None) -> FakeModels:
    models = FakeModels(response=response, error=error)
    monkeypatch.setattr(
        "app.rag.embeddings.get_client", lambda: SimpleNamespace(models=models)
    )
    return models


def test_normalize_returns_a_unit_vector():
    result = normalize([3.0, 4.0])
    assert result == pytest.approx([0.6, 0.8])
    assert math.sqrt(sum(value * value for value in result)) == pytest.approx(1.0)


def test_normalize_rejects_a_zero_vector():
    with pytest.raises(EmbeddingError, match="zero vector"):
        normalize([0.0, 0.0])


def test_empty_input_makes_no_request(monkeypatch):
    models = install_fake(monkeypatch)
    assert embed_texts([], QUERY_TASK) == []
    assert models.calls == []


def test_returns_normalized_vectors_in_order(monkeypatch):
    install_fake(monkeypatch, response=make_response([3.0, 4.0], [0.0, 2.0]))
    result = embed_texts(["a", "b"], DOCUMENT_TASK)
    assert result[0] == pytest.approx([0.6, 0.8])
    assert result[1] == pytest.approx([0.0, 1.0])


def test_request_uses_model_dimension_and_task_type(monkeypatch):
    models = install_fake(monkeypatch, response=make_response([1.0, 0.0]))
    embed_texts(["a"], QUERY_TASK)
    call = models.calls[0]
    assert call["model"] == settings.gemini_embedding_model
    assert call["contents"] == ["a"]
    assert call["config"].output_dimensionality == EMBEDDING_DIMENSION
    assert call["config"].task_type == QUERY_TASK


def test_wrong_embedding_count_is_rejected(monkeypatch):
    install_fake(monkeypatch, response=make_response([1.0, 0.0]))
    with pytest.raises(EmbeddingError, match="Expected 2"):
        embed_texts(["a", "b"], QUERY_TASK)


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (errors.ClientError(429, api_error_payload(429, "RESOURCE_EXHAUSTED")), 429),
        (errors.ServerError(503, api_error_payload(503, "UNAVAILABLE")), 503),
        (errors.ClientError(400, api_error_payload(400, "INVALID_ARGUMENT")), 400),
    ],
    ids=["rate-limit", "overloaded", "other"],
)
def test_api_errors_keep_their_status_code(monkeypatch, error, expected_status):
    install_fake(monkeypatch, error=error)
    with pytest.raises(EmbeddingError) as raised:
        embed_texts(["a"], QUERY_TASK)
    assert raised.value.status_code == expected_status
    assert raised.value.__cause__ is error


def test_local_failures_carry_no_status_code():
    with pytest.raises(EmbeddingError) as raised:
        normalize([0.0])
    assert raised.value.status_code is None


def test_response_without_values_is_an_embedding_error(monkeypatch):
    install_fake(monkeypatch, response=make_response(None))
    with pytest.raises(EmbeddingError):
        embed_texts(["a"], QUERY_TASK)


NETWORK_ERRORS = [
    (httpx.ConnectTimeout("https://example.invalid/?key=SECRET"), "in time"),
    (httpx.ReadTimeout("https://example.invalid/?key=SECRET"), "in time"),
    (httpx.ConnectError("https://example.invalid/?key=SECRET"), "Could not reach"),
]


@pytest.mark.parametrize(
    ("error", "expected"),
    NETWORK_ERRORS,
    ids=["connect-timeout", "read-timeout", "connect-error"],
)
def test_network_errors_become_embedding_errors(monkeypatch, error, expected):
    install_fake(monkeypatch, error=error)
    with pytest.raises(EmbeddingError, match=expected) as raised:
        embed_texts(["a"], QUERY_TASK)
    assert "SECRET" not in str(raised.value)
    assert raised.value.status_code is None
    assert raised.value.__cause__ is error