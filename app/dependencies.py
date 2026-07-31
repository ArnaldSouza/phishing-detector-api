"""Reusable FastAPI dependencies."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import InvalidTokenError, decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Resolve the authenticated user from a bearer token.

    Args:
        token: Bearer token taken from the Authorization header.
        db: Database session.

    Returns:
        The authenticated account.

    Raises:
        HTTPException: 401 if the token is invalid or the user no longer exists.
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        user_id = int(decode_access_token(token))
    except (InvalidTokenError, ValueError) as error:
        raise credentials_error from error

    user = db.get(User, user_id)
    if user is None:
        raise credentials_error
    return user
