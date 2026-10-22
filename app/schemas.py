"""Pydantic schemas for request and response payloads."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.security import BCRYPT_MAX_PASSWORD_BYTES

MAX_URL_LENGTH = 2048
MIN_PASSWORD_LENGTH = 8
# Bounds the prompt size and the free-tier quota spent on a single request.
MAX_EMAIL_TEXT_LENGTH = 10_000


class PredictionRequest(BaseModel):
    """Incoming request to classify a single URL."""

    url: str = Field(min_length=1, max_length=MAX_URL_LENGTH)
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class PredictionResponse(BaseModel):
    """Classification result returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    hostname: str
    is_phishing: bool
    phishing_probability: float
    created_at: datetime


class AnalysisRequest(BaseModel):
    """Incoming request to explain whether an email looks like phishing."""

    email_text: str = Field(min_length=1, max_length=MAX_EMAIL_TEXT_LENGTH)

    @field_validator("email_text")
    @classmethod
    def email_text_must_not_be_blank(cls, value: str) -> str:
        """Reject text with no visible content; the value is returned unchanged."""
        if not value.strip():
            raise ValueError("Email text must not be blank")
        return value


class HostnameSignal(BaseModel):
    """Classifier score for one hostname found in the email."""

    hostname: str
    phishing_probability: float


class AnalysisResponse(BaseModel):
    """Explanation generated for an email, with the evidence behind it."""

    id: int
    explanation: str
    signals: list[HostnameSignal]
    cited_slugs: list[str]
    prompt_identifier: str
    model: str
    created_at: datetime


class UserCreate(BaseModel):
    """Registration payload."""

    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH)

    @field_validator("password")
    @classmethod
    def password_must_fit_bcrypt(cls, value: str) -> str:
        """Reject passwords bcrypt cannot hash in full."""
        if len(value.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
            raise ValueError(
                f"Password must not exceed {BCRYPT_MAX_PASSWORD_BYTES} bytes"
            )
        return value


class UserResponse(BaseModel):
    """Public representation of an account."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    """Issued access token."""

    access_token: str
    token_type: str = "bearer"
