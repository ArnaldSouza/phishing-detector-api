"""Tests for versioned prompt loading."""

import pytest

from app.llm.prompts import PromptNotFoundError, load_prompt


def test_loads_the_versioned_prompt() -> None:
    prompt = load_prompt("explain_email", "v1")

    assert prompt.identifier == "explain_email/v1"
    assert "untrusted" in prompt.system


def test_unknown_version_raises() -> None:
    with pytest.raises(PromptNotFoundError):
        load_prompt("explain_email", "v999")


def test_email_text_is_inserted_verbatim() -> None:
    prompt = load_prompt("explain_email", "v1")
    email = "Pay $100 now {urgent} ${HOME}"

    rendered = prompt.render_user(email=email, signals="none", cases="none")

    assert email in rendered


def test_missing_value_raises() -> None:
    prompt = load_prompt("explain_email", "v1")

    with pytest.raises(KeyError):
        prompt.render_user(email="text")