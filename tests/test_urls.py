"""Tests for hostname extraction (pure functions, no network)."""

import pytest

from app.llm.urls import extract_hostnames, refang


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Pay here: http://parcel-fee-pay.example.com/track",
            ["parcel-fee-pay.example.com"],
        ),
        ("https://a.example.com/x?token=abc", ["a.example.com"]),
        ("HTTP://EXAMPLE.COM", ["example.com"]),
        ("example.com:8080/x", ["example.com"]),
        ("Go to example.com.", ["example.com"]),
        ("meusite.com.br/entrar", ["meusite.com.br"]),
        ("www.something.zzzz", ["www.something.zzzz"]),
        ("http://host.internal/x", ["host.internal"]),
    ],
)
def test_plain_urls_and_domains(text, expected):
    assert extract_hostnames(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("hxxps://evil[.]example[.]com/login", ["evil.example.com"]),
        ("hxxp[:]//evil[.]com", ["evil.com"]),
        ("HXXP://EVIL[.]COM", ["evil.com"]),
        ("visit evil(.)com now", ["evil.com"]),
        ("evil[dot]com", ["evil.com"]),
        ("evil{.}com", ["evil.com"]),
    ],
)
def test_defanged_urls(text, expected):
    assert extract_hostnames(text) == expected


def test_refang_only_rewrites_text():
    assert refang("hxxp://a[.]b[:]") == "http://a.b:"


@pytest.mark.parametrize(
    "text",
    [
        "arquivo.pdf",
        "v1.2.3",
        "report.final.docx",
        "see section 3.2",
        "Total: 1.234,56",
        "example.com.evil",
    ],
)
def test_false_positives_are_ignored(text):
    assert extract_hostnames(text) == []


@pytest.mark.parametrize(
    "text",
    ["write to support@example.com", "john.doe@example.com"],
)
def test_email_addresses_are_not_hostnames(text):
    assert extract_hostnames(text) == []


def test_userinfo_trick_returns_the_real_host():
    assert extract_hostnames("http://paypal.com@evil.com/login") == ["evil.com"]


def test_duplicates_are_removed_keeping_first_order():
    text = "http://b.com/1 http://a.com/2 http://B.com/3 a.com"
    assert extract_hostnames(text) == ["b.com", "a.com"]


def test_limit_caps_the_result():
    text = " ".join(f"site{i}.com" for i in range(15))
    assert len(extract_hostnames(text)) == 10
    assert extract_hostnames(text, limit=3) == [
        "site0.com",
        "site1.com",
        "site2.com",
    ]


def test_limit_must_be_positive():
    with pytest.raises(ValueError, match="limit"):
        extract_hostnames("a.com", limit=0)


def test_empty_text_returns_nothing():
    assert extract_hostnames("") == []


@pytest.mark.parametrize(
    "text",
    ["a" * 100_000, "http://" * 5_000, "a-" * 50_000],
    ids=["long-word", "repeated-scheme", "repeated-hyphen"],
)
def test_pathological_input_finishes(text):
    assert extract_hostnames(text) == []
