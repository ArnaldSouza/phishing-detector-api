"""Endpoints for URL phishing classification."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.ml.classifier import classify_url
from app.models import Prediction
from app.schemas import PredictionRequest, PredictionResponse
from app.dependencies import get_current_user
from app.models import Prediction, User

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_prediction(
    payload: PredictionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PredictionResponse:
    """Classify a URL and persist the result.

    Args:
        payload: URL to analyse and the decision threshold to apply.
        db: Database session.

    Returns:
        The stored classification result.
    """
    classification = classify_url(payload.url, threshold=payload.threshold)

    record = Prediction(
        url=classification.url,
        is_phishing=classification.is_phishing,
        phishing_probability=classification.phishing_probability,
        user_id=current_user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return PredictionResponse(
        id=record.id,
        url=record.url,
        hostname=classification.hostname,
        is_phishing=record.is_phishing,
        phishing_probability=record.phishing_probability,
        created_at=record.created_at,
    )