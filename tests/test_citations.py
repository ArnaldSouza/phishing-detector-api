"""Tests for citation extraction (pure function, no network)."""

import pytest

from app.llm.citations import extract_cited_slugs

ALLOWED = ["parcel-delivery-fee", "urgency-account-suspension"]


def test_returns_allowed_slugs_in_order_of_appearance():
    text = "See [urgency-account-suspension] and [parcel-delivery-fee]."
    assert extract_cited_slugs(text, ALLOWED) == [
        "urgency-account-suspension",
        "parcel-delivery-fee",
    ]


def test_invented_slugs_are_dropped():
    text = "Matches [parcel-delivery-fee] and [made-up-technique]."
    assert extract_cited_slugs(text, ALLOWED) == ["parcel-delivery-fee"]


def test_duplicates_are_removed():
    text = "[parcel-delivery-fee] again [parcel-delivery-fee]"
    assert extract_cited_slugs(text, ALLOWED) == ["parcel-delivery-fee"]


def test_matching_is_exact():
    assert extract_cited_slugs("[Parcel-Delivery-Fee]", ALLOWED) == []


def test_adjacent_citations_are_both_found():
    text = "[parcel-delivery-fee][urgency-account-suspension]"
    assert extract_cited_slugs(text, ALLOWED) == ALLOWED


def test_markdown_link_text_is_not_a_citation():
    assert extract_cited_slugs("[click here](http://a.example.com)", ALLOWED) == []


def test_slug_without_brackets_is_not_a_citation():
    assert extract_cited_slugs("parcel-delivery-fee", ALLOWED) == []


def test_nothing_allowed_means_nothing_cited():
    assert extract_cited_slugs("[parcel-delivery-fee]", []) == []


def test_empty_text():
    assert extract_cited_slugs("", ALLOWED) == []


@pytest.mark.parametrize(
    "text",
    ["[" * 100_000, "[a" * 50_000, "[" + "a" * 100_000],
    ids=["open-brackets", "repeated-open-a", "unclosed-long"],
)
def test_pathological_input_finishes(text):
    assert extract_cited_slugs(text, ALLOWED) == []
