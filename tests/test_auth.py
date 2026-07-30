"""Integration tests for registration and login."""

import pytest
from fastapi.testclient import TestClient

from app.models import User

REGISTER = "/auth/register"
LOGIN = "/auth/login"
VALID_PASSWORD = "test-password-123"


def test_registers_an_account(client: TestClient) -> None:
    response = client.post(
        REGISTER, json={"email": "new@example.com", "password": VALID_PASSWORD}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"
    assert "hashed_password" not in body
    assert "password" not in body


def test_rejects_duplicate_email(client: TestClient, test_user: User) -> None:
    response = client.post(
        REGISTER, json={"email": test_user.email, "password": VALID_PASSWORD}
    )
    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": VALID_PASSWORD},
        {"email": "user@example.com", "password": "short"},
        {"email": "user@example.com", "password": "a" * 73},
        {"email": "user@example.com"},
    ],
)
def test_rejects_invalid_registration(client: TestClient, payload: dict) -> None:
    assert client.post(REGISTER, json=payload).status_code == 422


def test_login_returns_a_bearer_token(client: TestClient, test_user: User) -> None:
    response = client.post(
        LOGIN, data={"username": test_user.email, "password": VALID_PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_rejects_wrong_password(client: TestClient, test_user: User) -> None:
    response = client.post(
        LOGIN, data={"username": test_user.email, "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_login_rejects_unknown_email(client: TestClient) -> None:
    response = client.post(
        LOGIN, data={"username": "nobody@example.com", "password": VALID_PASSWORD}
    )
    assert response.status_code == 401


def test_login_error_does_not_reveal_whether_email_exists(
    client: TestClient, test_user: User
) -> None:
    wrong_password = client.post(
        LOGIN, data={"username": test_user.email, "password": "wrong-password"}
    )
    unknown_email = client.post(
        LOGIN, data={"username": "nobody@example.com", "password": VALID_PASSWORD}
    )
    assert wrong_password.json() == unknown_email.json()


def test_issued_token_grants_access_to_predictions(
    client: TestClient, test_user: User
) -> None:
    token = client.post(
        LOGIN, data={"username": test_user.email, "password": VALID_PASSWORD}
    ).json()["access_token"]

    response = client.post(
        "/predictions",
        json={"url": "https://github.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201