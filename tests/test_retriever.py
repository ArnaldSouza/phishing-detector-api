"""Tests for similarity retrieval over the case knowledge base."""

import pytest
from sqlalchemy.orm import Session

from app.models import EMBEDDING_DIMENSION, PhishingCase
from app.rag.retriever import retrieve_similar_cases


def axis_vector(index: int) -> list[float]:
    """A unit vector along one axis, so distances are easy to reason about."""
    vector = [0.0] * EMBEDDING_DIMENSION
    vector[index] = 1.0
    return vector


@pytest.fixture
def seeded_cases(db_session: Session) -> None:
    db_session.add_all(
        PhishingCase(
            slug=f"case-{index}",
            title=f"Case {index}",
            content=f"Content {index}",
            embedding=axis_vector(index),
        )
        for index in range(3)
    )
    db_session.flush()


@pytest.mark.usefixtures("seeded_cases")
def test_orders_cases_by_similarity(db_session: Session) -> None:
    query = axis_vector(1)
    query[0] = 0.3

    results = retrieve_similar_cases(db_session, query)

    assert [case.slug for case in results] == ["case-1", "case-0", "case-2"]
    assert results[0].distance < results[1].distance < results[2].distance


@pytest.mark.usefixtures("seeded_cases")
def test_respects_the_limit(db_session: Session) -> None:
    assert len(retrieve_similar_cases(db_session, axis_vector(0), limit=2)) == 2


@pytest.mark.usefixtures("seeded_cases")
def test_max_distance_drops_unrelated_cases(db_session: Session) -> None:
    results = retrieve_similar_cases(db_session, axis_vector(1), max_distance=0.5)

    assert [case.slug for case in results] == ["case-1"]


def test_empty_knowledge_base_returns_nothing(db_session: Session) -> None:
    assert retrieve_similar_cases(db_session, axis_vector(0)) == []


def test_rejects_a_non_positive_limit(db_session: Session) -> None:
    with pytest.raises(ValueError):
        retrieve_similar_cases(db_session, axis_vector(0), limit=0)