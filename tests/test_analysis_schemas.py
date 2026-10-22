"""Tests for the analysis request schema."""

import pytest
from pydantic import ValidationError

from app.schemas import MAX_EMAIL_TEXT_LENGTH, AnalysisRequest


def test_accepts_text_at_the_limit():
    request = AnalysisRequest(email_text="a" * MAX_EMAIL_TEXT_LENGTH)
    assert len(request.email_text) == MAX_EMAIL_TEXT_LENGTH


def test_rejects_text_over_the_limit():
    with pytest.raises(ValidationError):
        AnalysisRequest(email_text="a" * (MAX_EMAIL_TEXT_LENGTH + 1))


@pytest.mark.parametrize(
    "text",
    ["", "   ", "\n\t \n"],
    ids=["empty", "spaces", "mixed"],
)
def test_rejects_empty_or_blank_text(text):
    with pytest.raises(ValidationError):
        AnalysisRequest(email_text=text)


def test_text_is_kept_exactly_as_sent():
    text = "  Hello\nworld  "
    assert AnalysisRequest(email_text=text).email_text == text
