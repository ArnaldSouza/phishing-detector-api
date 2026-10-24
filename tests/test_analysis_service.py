"""Tests for the email analysis service, with Gemini mocked."""

from collections.abc import Sequence

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.llm.client import Explanation, LLMError
from app.ml.classifier import Classification, classify_url
from app.models import EMBEDDING_DIMENSION, Analysis, PhishingCase, User
from app.rag.retriever import RetrievedCase
from app.services.analysis import analyze_email, hash_email

PROMPT_IDENTIFIER = "explain_email/v1"
MODEL_NAME = "test-model"
EMAIL_WITH_URL = "Verify your account now at paypa1-secure.com or it closes."
EMAIL_WITHOUT_URL = "Hi, are we still having lunch tomorrow?"

LlmCall = tuple[str, Sequence[Classification], Sequence[RetrievedCase]]


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


@pytest.fixture(autouse=True)
def stub_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every email embed to axis 0, so case-0 is always the closest."""
    monkeypatch.setattr(
        "app.services.analysis.embed_texts",
        lambda texts, task_type: [axis_vector(0)],
    )


def stub_llm(monkeypatch: pytest.MonkeyPatch, text: str) -> list[LlmCall]:
    """Replace the chat call with a fake and return the calls it receives."""
    calls: list[LlmCall] = []

    def fake_generate(
        email: str,
        classifications: Sequence[Classification],
        cases: Sequence[RetrievedCase],
    ) -> Explanation:
        calls.append((email, classifications, cases))
        return Explanation(
            text=text, prompt_identifier=PROMPT_IDENTIFIER, model=MODEL_NAME
        )

    monkeypatch.setattr("app.services.analysis.generate_explanation", fake_generate)
    return calls


def count_analyses(db_session: Session) -> int:
    return db_session.scalar(select(func.count()).select_from(Analysis)) or 0


@pytest.mark.usefixtures("seeded_cases")
def test_records_only_hash_and_metadata(
    db_session: Session, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = stub_llm(monkeypatch, "Suspicious domain, see [case-0].")
    expected_probability = classify_url("paypa1-secure.com").phishing_probability

    response = analyze_email(db_session, test_user.id, EMAIL_WITH_URL)

    record = db_session.get(Analysis, response.id)
    assert record is not None
    assert record.user_id == test_user.id
    assert record.email_hash == hash_email(EMAIL_WITH_URL)
    assert record.email_length == len(EMAIL_WITH_URL)
    assert record.prompt_identifier == PROMPT_IDENTIFIER
    assert record.model == MODEL_NAME
    assert record.hostnames == ["paypa1-secure.com"]
    assert record.cited_slugs == ["case-0"]
    assert record.max_phishing_probability == pytest.approx(expected_probability)

    assert response.explanation == "Suspicious domain, see [case-0]."
    assert [signal.hostname for signal in response.signals] == ["paypa1-secure.com"]
    assert response.cited_slugs == ["case-0"]

    email, classifications, cases = calls[0]
    assert email == EMAIL_WITH_URL
    assert [item.hostname for item in classifications] == ["paypa1-secure.com"]
    assert cases[0].slug == "case-0"


@pytest.mark.usefixtures("seeded_cases")
def test_email_without_urls_has_no_score(
    db_session: Session, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = stub_llm(monkeypatch, "No links to check.")

    response = analyze_email(db_session, test_user.id, EMAIL_WITHOUT_URL)

    record = db_session.get(Analysis, response.id)
    assert record is not None
    assert record.hostnames == []
    assert record.max_phishing_probability is None
    assert response.signals == []
    assert list(calls[0][1]) == []


@pytest.mark.usefixtures("seeded_cases")
def test_invented_slug_is_dropped_from_the_record_only(
    db_session: Session, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    text = "Matches [made-up-case] and [case-0]."
    stub_llm(monkeypatch, text)

    response = analyze_email(db_session, test_user.id, EMAIL_WITH_URL)

    record = db_session.get(Analysis, response.id)
    assert record is not None
    assert record.cited_slugs == ["case-0"]
    assert response.cited_slugs == ["case-0"]
    assert response.explanation == text


@pytest.mark.usefixtures("seeded_cases")
def test_llm_failure_saves_nothing(
    db_session: Session, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing_generate(*args: object, **kwargs: object) -> Explanation:
        raise LLMError("Gemini is overloaded.", status_code=503)

    monkeypatch.setattr("app.services.analysis.generate_explanation", failing_generate)

    with pytest.raises(LLMError):
        analyze_email(db_session, test_user.id, EMAIL_WITH_URL)

    assert count_analyses(db_session) == 0


@pytest.mark.usefixtures("seeded_cases")
def test_only_cases_within_the_distance_limit_reach_the_llm(
    db_session: Session, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = stub_llm(monkeypatch, "No match.")

    analyze_email(db_session, test_user.id, EMAIL_WITH_URL)

    cases = calls[0][2]
    assert [case.slug for case in cases] == ["case-0"]