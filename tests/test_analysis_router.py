"""Integration tests for the email analysis endpoint, with the service mocked."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.gemini import GeminiError
from app.models import User
from app.schemas import AnalysisResponse, HostnameSignal

ENDPOINT = "/analysis"
EMAIL_TEXT = "Verify your account at paypa1-secure.com or it will be closed."
SECRET_MESSAGE = "GEMINI_API_KEY is not set. Add it to your .env file."


def build_response() -> AnalysisResponse:
    return AnalysisResponse(
        id=1,
        explanation="Suspicious domain, see [case-0].",
        signals=[
            HostnameSignal(hostname="paypa1-secure.com", phishing_probability=0.84)
        ],
        cited_slugs=["case-0"],
        prompt_identifier="explain_email/v1",
        model="test-model",
        created_at=datetime.now(UTC),
    )


def stub_service_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.routers.analysis.analyze_email",
        lambda db, user_id, email_text: build_response(),
    )


def stub_service_failure(
    monkeypatch: pytest.MonkeyPatch, message: str, status_code: int | None
) -> None:
    def failing(db: object, user_id: int, email_text: str) -> AnalysisResponse:
        raise GeminiError(message, status_code=status_code)

    monkeypatch.setattr("app.routers.analysis.analyze_email", failing)


def test_requires_authentication(client: TestClient) -> None:
    assert client.post(ENDPOINT, json={"email_text": EMAIL_TEXT}).status_code == 401


def test_returns_created_with_complete_payload(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub_service_success(monkeypatch)

    response = auth_client.post(ENDPOINT, json={"email_text": EMAIL_TEXT})

    assert response.status_code == 201
    assert set(response.json()) == {
        "id",
        "explanation",
        "signals",
        "cited_slugs",
        "prompt_identifier",
        "model",
        "created_at",
    }


def test_passes_the_caller_and_the_text_to_the_service(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch, test_user: User
) -> None:
    received: list[tuple[int, str]] = []

    def spy(db: object, user_id: int, email_text: str) -> AnalysisResponse:
        received.append((user_id, email_text))
        return build_response()

    monkeypatch.setattr("app.routers.analysis.analyze_email", spy)

    auth_client.post(ENDPOINT, json={"email_text": EMAIL_TEXT})

    assert received == [(test_user.id, EMAIL_TEXT)]


def test_rate_limit_becomes_429(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub_service_failure(monkeypatch, "Gemini free-tier rate limit.", 429)

    response = auth_client.post(ENDPOINT, json={"email_text": EMAIL_TEXT})

    assert response.status_code == 429


@pytest.mark.parametrize("status_code", [503, 500, 400, None])
def test_any_other_failure_becomes_503(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch, status_code: int | None
) -> None:
    stub_service_failure(monkeypatch, "Gemini failed.", status_code)

    response = auth_client.post(ENDPOINT, json={"email_text": EMAIL_TEXT})

    assert response.status_code == 503


def test_error_body_leaks_neither_config_nor_email(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub_service_failure(monkeypatch, SECRET_MESSAGE, None)

    response = auth_client.post(ENDPOINT, json={"email_text": EMAIL_TEXT})

    assert "GEMINI_API_KEY" not in response.text
    assert ".env" not in response.text
    assert EMAIL_TEXT not in response.text


@pytest.mark.parametrize(
    "payload",
    [
        {"email_text": ""},
        {"email_text": "   \n\t  "},
        {"email_text": "a" * 10_001},
        {},
    ],
)
def test_rejects_invalid_payload(auth_client: TestClient, payload: dict) -> None:
    assert auth_client.post(ENDPOINT, json=payload).status_code == 422