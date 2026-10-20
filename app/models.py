from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgvector.sqlalchemy import Vector

from app.database import Base

# RFC 5321: 64 characters for the local part, 255 for the domain.
MAX_EMAIL_LENGTH = 320
# bcrypt hashes are 60 characters; the extra room allows migrating algorithms.
MAX_HASH_LENGTH = 128
MAX_URL_LENGTH = 2048

EMBEDDING_DIMENSION = 768
MAX_CASE_TITLE_LENGTH = 200


class User(Base):
    """An account authorised to request URL classifications."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        String(MAX_EMAIL_LENGTH), unique=True, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(MAX_HASH_LENGTH))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    predictions: Mapped[list["Prediction"]] = relationship(back_populates="user")


class Prediction(Base):
    """Stores the result of a single URL phishing analysis."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(MAX_URL_LENGTH), index=True)
    is_phishing: Mapped[bool]
    phishing_probability: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    user: Mapped["User"] = relationship(back_populates="predictions")


class PhishingCase(Base):
    """A curated phishing technique used as retrieval context for explanations."""

    __tablename__ = "phishing_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(MAX_CASE_TITLE_LENGTH), unique=True)
    title: Mapped[str] = mapped_column(String(MAX_CASE_TITLE_LENGTH))
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
