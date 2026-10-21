"""Build the user message for the explain_email prompt from typed inputs."""

from collections.abc import Sequence

from app.llm.prompts import PromptTemplate
from app.llm.sanitize import escape_email_delimiters
from app.ml.classifier import Classification
from app.rag.retriever import RetrievedCase

NO_SIGNALS_TEXT = "No URLs found in the email."
NO_CASES_TEXT = "No matching reference cases."
CASE_SEPARATOR = "\n\n---\n\n"


def format_signals(classifications: Sequence[Classification]) -> str:
    """Describe the classifier output, one line per hostname.

    Only the hostname is included: the classifier never sees the rest of the
    URL, and the rest may carry personal data.
    """
    if not classifications:
        return NO_SIGNALS_TEXT
    return "\n".join(
        f"- {item.hostname}: phishing probability {item.phishing_probability:.2f}"
        for item in classifications
    )


def format_cases(cases: Sequence[RetrievedCase]) -> str:
    """Render each retrieved case as ``[slug]`` followed by its full content."""
    if not cases:
        return NO_CASES_TEXT
    return CASE_SEPARATOR.join(f"[{case.slug}]\n{case.content}" for case in cases)


def build_user_message(
    prompt: PromptTemplate,
    email: str,
    classifications: Sequence[Classification],
    cases: Sequence[RetrievedCase],
) -> str:
    """Fill the prompt template, escaping the untrusted email text first."""
    return prompt.render_user(
        email=escape_email_delimiters(email),
        signals=format_signals(classifications),
        cases=format_cases(cases),
    )
