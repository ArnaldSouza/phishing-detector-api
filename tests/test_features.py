"""Tests for URL hostname feature extraction."""

import pytest

from app.ml.features import (
    FEATURE_NAMES,
    extract_features,
    extract_hostname,
    to_vector,
)


def test_extract_features_returns_every_declared_feature() -> None:
    features = extract_features("https://example.com")
    assert set(features) == set(FEATURE_NAMES)


def test_to_vector_preserves_feature_names_order() -> None:
    features = {name: float(index) for index, name in enumerate(FEATURE_NAMES)}
    expected = [float(index) for index in range(len(FEATURE_NAMES))]
    assert to_vector(features) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.example.com", "example.com"),
        ("https://example.com", "example.com"),
        ("example.com", "example.com"),
        ("http://EXAMPLE.com/login?id=1", "example.com"),
        ("https://www.sub.example.com", "sub.example.com"),
    ],
)
def test_extract_hostname_normalizes_input(url: str, expected: str) -> None:
    assert extract_hostname(url) == expected


@pytest.mark.parametrize(
    ("with_path", "without_path"),
    [
        ("https://example.com/very/long/path?token=abc", "https://example.com"),
        ("http://example.com/login", "https://example.com"),
    ],
)
def test_path_and_scheme_do_not_affect_features(
    with_path: str, without_path: str
) -> None:
    assert extract_features(with_path) == extract_features(without_path)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://192.168.0.1/login", 1.0),
        ("http://8.8.8.8", 1.0),
        ("https://example.com", 0.0),
        ("https://1234.example.com", 0.0),
    ],
)
def test_detects_raw_ip_hostname(url: str, expected: float) -> None:
    assert extract_features(url)["has_ip_host"] == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://secure-login.tk", 1.0),
        ("https://example.xyz", 1.0),
        ("https://example.com", 0.0),
        ("https://uni-mainz.de", 0.0),
    ],
)
def test_flags_suspicious_tld(url: str, expected: float) -> None:
    assert extract_features(url)["has_suspicious_tld"] == expected


def test_detects_punycode_hostname() -> None:
    assert extract_features("https://xn--pypal-4ve.com")["is_punycode"] == 1.0
    assert extract_features("https://paypal.com")["is_punycode"] == 0.0


def test_random_hostname_has_higher_entropy_than_dictionary_word() -> None:
    random_like = extract_features("https://x7fk2m9qzp.com")["entropy"]
    word_like = extract_features("https://aaaaaaaaaa.com")["entropy"]
    assert random_like > word_like


def test_digit_ratio_is_normalized_by_hostname_length() -> None:
    features = extract_features("https://a1b2.com")
    assert features["digit_ratio"] == pytest.approx(2 / len("a1b2.com"))


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://example.com", 2.0),
        ("https://login.example.com", 3.0),
        ("https://www.example.com", 2.0),
    ],
)
def test_counts_hostname_labels(url: str, expected: float) -> None:
    assert extract_features(url)["num_labels"] == expected


def test_handles_empty_url_without_raising() -> None:
    vector = to_vector(extract_features(""))
    assert len(vector) == len(FEATURE_NAMES)
    assert all(value == 0.0 for value in vector)