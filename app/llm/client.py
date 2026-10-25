"""Generate the email explanation with the Gemini chat model."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

import httpx
from google.genai import errors, types

from app.config import settings
from app.gemini import (
    GeminiError,
    describe_api_error,
    describe_network_error,
    get_client,
)
from app.llm.prompt_builder import build_user_message
from app.llm.prompts import load_prompt
from app.ml.classifier import Classification
from app.rag.retriever import RetrievedCase

PROMPT_NAME: Final[str] = "explain_email"
PROMPT_VERSION: Final[str] = "v1"
# Thinking tokens count against this limit (a 60-token cap returned no text),
# so it must leave room for both the reasoning and the answer.
MAX_OUTPUT_TOKENS: Final[int] = 4096
TEMPERATURE: Final[float] = 0.2


class LLMError(GeminiError):
    """Raised when the chat model cannot produce a usable explanation."""
    


@dataclass(frozen=True)
class Explanation:
    """A generated explanation and what is needed to reproduce it."""

    text: str
    prompt_identifier: str
    model: str


def _extract_text(response: types.GenerateContentResponse) -> str:
    """Return the answer text, or raise if the response is not complete."""
    candidates = response.candidates or []
    if not candidates:
        raise LLMError("Gemini returned no answer (the request may be blocked).")

    finish_reason = candidates[0].finish_reason
    if finish_reason != types.FinishReason.STOP:
        name = finish_reason.name if finish_reason else "unknown"
        raise LLMError(f"Gemini did not finish the answer (reason: {name}).")

    text = (response.text or "").strip()
    if not text:
        raise LLMError("Gemini returned an empty answer.")
    return text


def generate_explanation(
    email: str,
    classifications: Sequence[Classification],
    cases: Sequence[RetrievedCase],
) -> Explanation:
    """Explain whether an email looks like phishing, citing retrieved cases.

    Args:
        email: Untrusted email text. It is escaped before use.
        classifications: Classifier results for the hostnames in the email.
        cases: Knowledge base cases retrieved for the email.

    Raises:
        GeminiError: If the API key is missing.
        LLMError: If the request fails or the answer is incomplete or empty.
    """
    prompt = load_prompt(PROMPT_NAME, PROMPT_VERSION)
    user_message = build_user_message(prompt, email, classifications, cases)

    try:
        response = get_client().models.generate_content(
            model=settings.gemini_model,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=prompt.system,
                temperature=TEMPERATURE,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            ),
        )
    except errors.APIError as error:
        raise LLMError(
            describe_api_error(error, "chat"), status_code=error.code
        ) from error
    except httpx.HTTPError as error:
        raise LLMError(describe_network_error(error)) from error

    return Explanation(
        text=_extract_text(response),
        prompt_identifier=prompt.identifier,
        model=settings.gemini_model,
    )
