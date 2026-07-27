"""Feature extraction from URL hostnames for phishing classification.

Features are derived from the hostname only. Scheme and path are discarded
because in the training dataset they encode collection artifacts rather than
phishing signal.
"""

import math
import re
from collections import Counter
from urllib.parse import urlparse

FEATURE_NAMES: tuple[str, ...] = (
    "hostname_length",
    "num_labels",
    "longest_label_length",
    "num_dots",
    "num_hyphens",
    "num_digits",
    "digit_ratio",
    "entropy",
    "tld_length",
    "has_suspicious_tld",
    "has_ip_host",
    "is_punycode",
)

# Free or loosely moderated TLDs frequently abused for phishing.
# Heuristic prior: this list encodes domain knowledge and may become stale.
SUSPICIOUS_TLDS: frozenset[str] = frozenset(
    {
        "tk", "ml", "ga", "cf", "gq", "xyz", "top", "buzz", "click",
        "link", "work", "live", "icu", "pw", "cc", "su", "online",
        "site", "fit", "rest", "bar", "cam", "monster", "surf", "quest",
    }
)

_IPV4_PATTERN = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")
_WWW_PREFIX = "www."


def extract_hostname(url: str) -> str:
    """Extract a normalized hostname from a URL.

    Adds a scheme when missing so parsing is reliable, lowercases the result,
    and strips a leading ``www.`` so its presence cannot act as a class signal.

    Args:
        url: Raw URL or bare hostname.

    Returns:
        Normalized hostname, or an empty string when none can be parsed.
    """
    candidate = url if "://" in url else f"http://{url}"
    hostname = (urlparse(candidate).hostname or "").lower()
    if hostname.startswith(_WWW_PREFIX):
        return hostname[len(_WWW_PREFIX):]
    return hostname


def _shannon_entropy(value: str) -> float:
    """Compute Shannon entropy of a string, in bits per character."""
    if not value:
        return 0.0
    total = len(value)
    counts = Counter(value)
    return -sum(
        (count / total) * math.log2(count / total) for count in counts.values()
    )


def _has_ip_host(hostname: str) -> bool:
    """Check whether the hostname is a raw IPv4 address instead of a domain."""
    return bool(_IPV4_PATTERN.match(hostname))


def _tld(hostname: str) -> str:
    """Return the last label of the hostname, or an empty string."""
    if "." not in hostname:
        return ""
    return hostname.rsplit(".", maxsplit=1)[-1]


def extract_features(url: str) -> dict[str, float]:
    """Extract numeric features from a URL hostname.

    Features are computed from the string only; the URL is never fetched.

    Args:
        url: Raw URL or bare hostname, with or without a scheme.

    Returns:
        Mapping of feature name to numeric value.
    """
    hostname = extract_hostname(url)
    labels = hostname.split(".") if hostname else []
    digits = sum(char.isdigit() for char in hostname)
    tld = _tld(hostname)

    return {
        "hostname_length": float(len(hostname)),
        "num_labels": float(len(labels)),
        "longest_label_length": float(max((len(label) for label in labels), default=0)),
        "num_dots": float(hostname.count(".")),
        "num_hyphens": float(hostname.count("-")),
        "num_digits": float(digits),
        "digit_ratio": digits / len(hostname) if hostname else 0.0,
        "entropy": _shannon_entropy(hostname),
        "tld_length": float(len(tld)),
        "has_suspicious_tld": float(tld in SUSPICIOUS_TLDS),
        "has_ip_host": float(_has_ip_host(hostname)),
        "is_punycode": float("xn--" in hostname),
    }


def to_vector(features: dict[str, float]) -> list[float]:
    """Convert a feature mapping into an ordered vector matching FEATURE_NAMES."""
    return [features[name] for name in FEATURE_NAMES]