"""Extract hostnames from untrusted email text, without touching the network."""

import re
from typing import Final

DEFAULT_LIMIT: Final[int] = 10

# Bare domains (no scheme, no "www.") count only with one of these TLDs.
# This avoids false positives such as "file.pdf" or "v1.2.3". Extend it when a
# real phishing domain is missed.
COMMON_TLDS: Final[frozenset[str]] = frozenset(
    {
        "com", "net", "org", "info", "biz", "xyz", "top", "online", "site",
        "click", "link", "shop", "store", "live", "icu", "vip", "club",
        "buzz", "cloud", "work", "support", "cc", "io", "tk", "ml", "ga",
        "cf", "gq", "br", "pt", "ar", "mx", "uk", "de", "fr", "ru", "cn",
    }
)  # fmt: skip

# Defanged forms: hxxp://, [.] (.) {.} [dot], and [:].
_DEFANGED_SCHEME: Final[re.Pattern[str]] = re.compile(r"hxxp", re.IGNORECASE)
_DEFANGED_DOT: Final[re.Pattern[str]] = re.compile(
    r"[\[({]\s*(?:\.|dot)\s*[\])}]", re.IGNORECASE
)
_DEFANGED_COLON: Final[re.Pattern[str]] = re.compile(r"[\[({]\s*:\s*[\])}]")

_LABEL: Final[str] = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_CANDIDATE: Final[re.Pattern[str]] = re.compile(
    # Not in the middle of a word, an email address or a longer domain.
    r"(?<![a-z0-9@.-])"
    # Optional scheme, plus userinfo ("paypal.com@") that must be ignored.
    r"(?:(?P<scheme>https?://)(?:[^\s/@]{1,100}@)?)?"
    rf"(?P<host>(?:{_LABEL}\.)+(?P<tld>[a-z]{{2,24}}))"
    # The host must end here: no more labels, no "@" (email local part).
    r"(?![a-z0-9@-]|\.[a-z0-9])",
    re.IGNORECASE,
)


def refang(text: str) -> str:
    """Rewrite defanged URLs ("hxxp://a[.]com") into their plain form.

    This only rewrites text. Nothing is ever requested.
    """
    text = _DEFANGED_SCHEME.sub("http", text)
    text = _DEFANGED_COLON.sub(":", text)
    return _DEFANGED_DOT.sub(".", text)


def _is_accepted(match: re.Match[str]) -> bool:
    """Accept explicit URLs and "www." hosts; bare domains need a known TLD."""
    host = match["host"].lower()
    has_explicit_marker = match["scheme"] is not None or host.startswith("www.")
    return has_explicit_marker or match["tld"].lower() in COMMON_TLDS


def extract_hostnames(text: str, limit: int = DEFAULT_LIMIT) -> list[str]:
    """Return the distinct hostnames found in ``text``, in order of appearance.

    Handles ``http(s)://`` URLs, ``www.`` hosts, bare domains with a common
    TLD, and defanged forms. Paths, queries and credentials are dropped.

    Args:
        text: Untrusted email text.
        limit: Maximum number of hostnames to return.

    Raises:
        ValueError: If ``limit`` is less than 1.
    """
    if limit < 1:
        raise ValueError("limit must be at least 1")

    hostnames: list[str] = []
    for match in _CANDIDATE.finditer(refang(text)):
        if not _is_accepted(match):
            continue
        hostname = match["host"].lower()
        if hostname in hostnames:
            continue
        hostnames.append(hostname)
        if len(hostnames) == limit:
            break
    return hostnames
