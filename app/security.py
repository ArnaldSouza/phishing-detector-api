"""Password hashing and JWT access token handling."""

from datetime import UTC, datetime, timedelta
from typing import Final

import bcrypt
import jwt

from app.config import settings

_ENCODING: Final[str] = "utf-8"

# bcrypt silently truncates input beyond this length; callers must reject
# longer passwords so that the extra characters are not misleading.
BCRYPT_MAX_PASSWORD_BYTES: Final[int] = 72


class InvalidTokenError(Exception):
    """Raised when an access token is malformed, expired, or badly signed."""


def hash_password(password: str) -> str:
    """Hash a plaintext password with a freshly generated salt."""
    return bcrypt.hashpw(password.encode(_ENCODING), bcrypt.gensalt()).decode(_ENCODING)


def verify_password(password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    return bcrypt.checkpw(password.encode(_ENCODING), hashed_password.encode(_ENCODING))


def create_access_token(subject: str) -> str:
    """Issue a signed access token identifying the given subject.

    Args:
        subject: Stable user identifier stored in the ``sub`` claim.

    Returns:
        Encoded JWT string.
    """
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "exp": expires_at}
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str) -> str:
    """Validate an access token and return its subject.

    Args:
        token: Encoded JWT string.

    Returns:
        The ``sub`` claim.

    Raises:
        InvalidTokenError: If the signature, expiry, or payload is invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as error:
        raise InvalidTokenError("Could not validate access token") from error

    subject = payload.get("sub")
    if not subject:
        raise InvalidTokenError("Access token is missing the subject claim")
    return subject
