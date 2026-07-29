"""Pydantic schemas for request and response payloads."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

MAX_URL_LENGTH = 2048


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