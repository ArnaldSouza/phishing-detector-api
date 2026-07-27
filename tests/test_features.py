"""Tests for URL feature extraction."""

import pytest

from app.ml.features import FEATURE_NAMES, extract_features, to_vector


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
        ("https://example.com", 0.0),
        ("https://www.example.com", 1.0),
        ("https://login.secure.example.com", 2.0),
    ],
)
def test_counts_subdomains(url: str, expected: float) -> None:
    assert extract_features(url)["num_subdomains"] == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://example.com", 1.0),
        ("http://example.com", 0.0),
        ("example.com", 0.0),
    ],
)
def test_detects_https_scheme(url: str, expected: float) -> None:
    assert extract_features(url)["uses_https"] == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://example.com", 0.0),
        ("https://example.com/?id=1", 1.0),
        ("https://example.com/?id=1&token=abc", 2.0),
    ],
)
def test_counts_query_parameters(url: str, expected: float) -> None:
    assert extract_features(url)["num_query_params"] == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://user@evil.example.com", 1.0),
        ("https://example.com", 0.0),
    ],
)
def test_detects_at_symbol(url: str, expected: float) -> None:
    assert extract_features(url)["has_at_symbol"] == expected


def test_parses_hostname_when_scheme_is_missing() -> None:
    features = extract_features("example.com/login")
    assert features["hostname_length"] == len("example.com")
    assert features["path_length"] == len("/login")


def test_handles_empty_url_without_raising() -> None:
    vector = to_vector(extract_features(""))
    assert len(vector) == len(FEATURE_NAMES)