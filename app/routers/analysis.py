"""Endpoint that explains whether an email looks like phishing."""

import logging
from typing import Final

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.gemini import RATE_LIMIT_STATUS, GeminiError
from app.models import User
from app.schemas import AnalysisRequest, AnalysisResponse
from app.services.analysis import analyze_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])

RATE_LIMITED_DETAIL: Final[str] = "Analysis quota reached. Try again in a minute."
UNAVAILABLE_DETAIL: Final[str] = "Analysis is temporarily unavailable."


def _to_http_error(error: GeminiError) -> HTTPException:
    """Map a Gemini failure to a client-safe HTTP error.

    The internal message can mention configuration (such as the API key
    variable), so it goes to the server log and never to the client.
    """
    logger.error("Gemini failure (status=%s): %s", error.status_code, error)
    if error.status_code == RATE_LIMIT_STATUS:
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=RATE_LIMITED_DETAIL,
        )
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=UNAVAILABLE_DETAIL,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_analysis(
    payload: AnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    """Explain whether an email looks like phishing.

    The email text is sent to Google's Gemini API to produce the explanation.
    Do not submit emails that contain other people's personal data. Only a
    hash of the email is stored, never its text or the explanation.

    Args:
        payload: Email text to analyse.
        current_user: Authenticated owner of the analysis.
        db: Database session.

    Returns:
        The explanation with the evidence behind it.
    """
    try:
        return analyze_email(db, current_user.id, payload.email_text)
    except GeminiError as error:
        raise _to_http_error(error) from error