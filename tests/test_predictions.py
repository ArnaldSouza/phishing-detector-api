"""Integration tests for the prediction endpoint."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Prediction

ENDPOINT = "/predictions"


def test_returns_created_with_complete_payload(client: TestClient) -> None:
    response = client.post(ENDPOINT, json={"url": "https://github.com"})

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {
        "id",
        "url",
        "hostname",
        "is_phishing",
        "phishing_probability",
        "created_at",
    }
    assert body["url"] == "https://github.com"
    assert isinstance(body["is_phishing"], bool)
    assert 0.0 <= body["phishing_probability"] <= 1.0


def test_persists_the_classification(client: TestClient, db_session: Session) -> None:
    response = client.post(ENDPOINT, json={"url": "https://example.com"})

    stored = db_session.get(Prediction, response.json()["id"])
    assert stored is not None
    assert stored.url == "https://example.com"
    assert stored.phishing_probability == response.json()["phishing_probability"]


def test_response_hostname_is_normalized(client: TestClient) -> None:
    response = client.post(ENDPOINT, json={"url": "https://www.Example.com/login"})
    assert response.json()["hostname"] == "example.com"


def test_threshold_zero_always_flags_as_phishing(client: TestClient) -> None:
    response = client.post(
        ENDPOINT, json={"url": "https://github.com", "threshold": 0.0}
    )
    assert response.json()["is_phishing"] is True


def test_threshold_one_never_flags_as_phishing(client: TestClient) -> None:
    response = client.post(
        ENDPOINT, json={"url": "http://secure-login-paypal-verify.tk", "threshold": 1.0}
    )
    assert response.json()["is_phishing"] is False


def test_default_threshold_is_applied_when_omitted(client: TestClient) -> None:
    with_default = client.post(ENDPOINT, json={"url": "https://github.com"}).json()
    explicit = client.post(
        ENDPOINT, json={"url": "https://github.com", "threshold": 0.5}
    ).json()
    assert with_default["is_phishing"] == explicit["is_phishing"]


@pytest.mark.parametrize(
    "payload",
    [
        {"url": ""},
        {"url": "https://example.com", "threshold": -0.1},
        {"url": "https://example.com", "threshold": 1.1},
        {"url": "https://example.com/" + "a" * 3000},
        {"threshold": 0.5},
    ],
)
def test_rejects_invalid_payload(client: TestClient, payload: dict) -> None:
    assert client.post(ENDPOINT, json=payload).status_code == 422


def test_health_endpoints_respond(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/health/db").json()["database"] == "connected"


@pytest.mark.model_dependent
def test_flags_an_obviously_suspicious_hostname(client: TestClient) -> None:
    response = client.post(
        ENDPOINT, json={"url": "http://secure-login-paypal-verify.tk"}
    )
    assert response.json()["phishing_probability"] > 0.5