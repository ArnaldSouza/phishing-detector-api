"""Retrieve the knowledge base cases most similar to a query embedding."""

from dataclasses import dataclass
from typing import Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PhishingCase

DEFAULT_LIMIT: Final[int] = 3


@dataclass(frozen=True)
class RetrievedCase:
    """A knowledge base case with its cosine distance to the query (lower is closer)."""

    slug: str
    title: str
    content: str
    distance: float


def retrieve_similar_cases(
    session: Session,
    query_embedding: list[float],
    limit: int = DEFAULT_LIMIT,
    max_distance: float | None = None,
) -> list[RetrievedCase]:
    """Return the cases closest to ``query_embedding``, nearest first.

    Args:
        session: Database session.
        query_embedding: Normalized vector of the text being analysed.
        limit: Maximum number of cases to return.
        max_distance: When set, drop cases farther than this cosine distance.

    Raises:
        ValueError: If ``limit`` is less than 1.
    """
    if limit < 1:
        raise ValueError("limit must be at least 1")

    distance = PhishingCase.embedding.cosine_distance(query_embedding)
    statement = (
        select(PhishingCase, distance.label("distance"))
        .order_by(distance)
        .limit(limit)
    )
    if max_distance is not None:
        statement = statement.where(distance <= max_distance)

    return [
        RetrievedCase(
            slug=case.slug,
            title=case.title,
            content=case.content,
            distance=float(case_distance),
        )
        for case, case_distance in session.execute(statement).all()
    ]