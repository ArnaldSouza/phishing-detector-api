"""Pydantic schemas for request and response payloads."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.security import BCRYPT_MAX_PASSWORD_BYTES

MAX_URL_LENGTH = 2048
MIN_PASSWORD_LENGTH = 8


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