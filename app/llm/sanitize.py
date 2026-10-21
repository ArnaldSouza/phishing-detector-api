"""Neutralize untrusted email text before it is placed inside the prompt."""

import re
from typing import Final

# Matches the "<" that opens an <email> or </email> tag, in any letter case and
# with optional whitespace ("</ EMAIL"). The closing ">" is not required, so a
# truncated tag cannot slip through.
_EMAIL_TAG_OPENER: Final[re.Pattern[str]] = re.compile(
    r"<(?=\s*/?\s*email)", re.IGNORECASE
)
ESCAPED_OPENER: Final[str] = "&lt;"


def escape_email_delimiters(text: str) -> str:
    """Escape anything that could close or reopen the ``<email>`` block.

    The prompt wraps the email in ``<email>`` tags and tells the model to treat
    the content as data. Without this step, an email containing ``</email>``
    could end the block early and place its own text outside it.
    """
    return _EMAIL_TAG_OPENER.sub(ESCAPED_OPENER, text)
