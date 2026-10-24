"""Orchestrate an email analysis: classify, retrieve, explain and record."""

import hashlib
from collections.abc import Sequence
from typing import Final

from sqlalchemy.orm import Session

from app.llm.citations import extract_cited_slugs
from app.llm.client import generate_explanation
from app.llm.urls import extract_hostnames
from app.ml.classifier import Classification, classify_url
from app.models import Analysis
from app.rag.embeddings import QUERY_TASK, embed_texts
from app.rag.retriever import retrieve_similar_cases
from app.schemas import AnalysisResponse, HostnameSignal

# Starting point from two sample emails (phishing cases at 0.32-0.38, an
# ordinary email at 0.41+). Review with a larger set of real emails.
MAX_CASE_DISTANCE: Final[float] = 0.39


def hash_email(email_text: str) -> str:
    """Return the SHA-256 hex digest of the email, so the text is never stored."""
    return hashlib.sha256(email_text.encode("utf-8")).hexdigest()


def _highest_probability(classifications: Sequence[Classification]) -> float | None:
    """Return the highest phishing probability, or None when there are no URLs."""
    return max(
        (item.phishing_probability for item in classifications), default=None
    )


def analyze_email(db: Session, user_id: int, email_text: str) -> AnalysisResponse:
    """Explain whether an email looks like phishing and record the metadata.

    The analysis is saved only after the explanation exists, so a Gemini
    failure leaves nothing in the database.

    Args:
        db: Database session.
        user_id: Owner of the analysis.
        email_text: Untrusted email text. It is never stored or logged.

    Raises:
        GeminiError: If the API key is missing.
        EmbeddingError: If the email cannot be embedded.
        LLMError: If the explanation cannot be generated.
    """
    classifications = [
        classify_url(hostname) for hostname in extract_hostnames(email_text)
    ]

    query_embedding = embed_texts([email_text], QUERY_TASK)[0]
    cases = retrieve_similar_cases(
        db, query_embedding, max_distance=MAX_CASE_DISTANCE
    )

    explanation = generate_explanation(email_text, classifications, cases)
    cited_slugs = extract_cited_slugs(
        explanation.text, [case.slug for case in cases]
    )

    analysis = Analysis(
        email_hash=hash_email(email_text),
        email_length=len(email_text),
        prompt_identifier=explanation.prompt_identifier,
        model=explanation.model,
        hostnames=[item.hostname for item in classifications],
        cited_slugs=cited_slugs,
        max_phishing_probability=_highest_probability(classifications),
        user_id=user_id,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return AnalysisResponse(
        id=analysis.id,
        explanation=explanation.text,
        signals=[
            HostnameSignal(
                hostname=item.hostname,
                phishing_probability=item.phishing_probability,
            )
            for item in classifications
        ],
        cited_slugs=cited_slugs,
        prompt_identifier=analysis.prompt_identifier,
        model=analysis.model,
        created_at=analysis.created_at,
    )