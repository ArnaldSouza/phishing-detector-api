"""Feature extraction from raw URL strings for phishing classification."""

import re
from urllib.parse import ParseResult, urlparse

FEATURE_NAMES: tuple[str, ...] = (
    "url_length",
    "hostname_length",
    "path_length",
    "num_dots",
    "num_hyphens",
    "num_digits",
    "num_query_params",
    "num_subdomains",
    "has_ip_host",
    "has_at_symbol",
    "uses_https",
)


_IPV4_PATTERN = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")


def _normalize(url: str) -> str:
    """Prepend a scheme when missing so the URL can be parsed reliably."""
    if "://" not in url:
        return f"http://{url}"
    return url


def _count_subdomains(hostname: str) -> int:
    """Count labels beyond the registrable domain (e.g. a.b.example.com -> 2)."""
    labels = hostname.split(".")
    return max(len(labels) - 2, 0)


def _has_ip_host(hostname: str) -> bool:
    """Check whether the hostname is a raw IPv4 address instead of a domain."""
    return bool(_IPV4_PATTERN.match(hostname))


def _count_query_params(parsed: ParseResult) -> int:
    """Count non-empty query string parameters."""
    return len([param for param in parsed.query.split("&") if param])


def extract_features(url: str) -> dict[str, float]:
    """Extract numeric features from a URL.

    Features are computed from the URL string only; the URL is never fetched.

    Args:
        url: Raw URL, with or without a scheme.

    Returns:
        Mapping of feature name to numeric value.
    """
    normalized = _normalize(url)
    parsed = urlparse(normalized)
    hostname = parsed.hostname or ""

    return {
        "url_length": float(len(normalized)),
        "hostname_length": float(len(hostname)),
        "path_length": float(len(parsed.path)),
        "num_dots": float(normalized.count(".")),
        "num_hyphens": float(normalized.count("-")),
        "num_digits": float(sum(char.isdigit() for char in normalized)),
        "num_query_params": float(_count_query_params(parsed)),
        "num_subdomains": float(_count_subdomains(hostname)),
        "has_ip_host": float(_has_ip_host(hostname)),
        "has_at_symbol": float("@" in normalized),
        "uses_https": float(parsed.scheme == "https"),
    }


def to_vector(features: dict[str, float]) -> list[float]:
    """Convert a feature mapping into an ordered vector matching FEATURE_NAMES."""
    return [features[name] for name in FEATURE_NAMES]