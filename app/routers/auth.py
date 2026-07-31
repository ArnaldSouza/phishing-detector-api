"""Endpoints for account registration and token issuance."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import Token, UserCreate, UserResponse
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    """Create an account.

    Args:
        payload: Email and plaintext password.
        db: Database session.

    Returns:
        The created account, without credentials.

    Raises:
        HTTPException: 409 if the email is already registered.
    """
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from error

    db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """Exchange credentials for an access token.

    Args:
        form_data: Form fields ``username`` (the email) and ``password``.
        db: Database session.

    Returns:
        A bearer token identifying the account.

    Raises:
        HTTPException: 401 if the credentials do not match.
    """
    user = db.scalar(select(User).where(User.email == form_data.username))

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Token(access_token=create_access_token(str(user.id)))
