"""Find which retrieved cases an explanation cites."""

import re
from collections.abc import Collection
from typing import Final

# Anything in square brackets without spaces. The length cap matches the
# database column and keeps the pattern linear on hostile input.
_BRACKETED: Final[re.Pattern[str]] = re.compile(r"\[([^\[\]\s]{1,200})\]")


def extract_cited_slugs(text: str, allowed_slugs: Collection[str]) -> list[str]:
    """Return the allowed slugs cited as ``[slug]``, without duplicates.

    A slug the model invented is dropped here, so only slugs that were really
    given to it are ever stored.

    Args:
        text: The generated explanation.
        allowed_slugs: Slugs of the cases that were sent to the model.
    """
    allowed = set(allowed_slugs)
    cited: list[str] = []
    for match in _BRACKETED.finditer(text):
        slug = match[1]
        if slug in allowed and slug not in cited:
            cited.append(slug)
    return cited
