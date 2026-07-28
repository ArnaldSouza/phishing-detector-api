"""Load the trained model and classify URLs at serving time."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

import joblib

from app.ml.features import FEATURE_NAMES, extract_features, extract_hostname, to_vector

MODEL_PATH: Final[Path] = (
    Path(__file__).resolve().parents[2] / "ml" / "artifacts" / "classifier.joblib"
)
DEFAULT_THRESHOLD: Final[float] = 0.5
PHISHING_CLASS: Final[int] = 1


@dataclass(frozen=True)
class Classification:
    """Result of classifying a single URL."""

    url: str
    hostname: str
    is_phishing: bool
    phishing_probability: float


class ModelNotFoundError(RuntimeError):
    """Raised when the serialized model bundle is missing."""


class FeatureMismatchError(RuntimeError):
    """Raised when the model was trained on a different feature set."""


@lru_cache(maxsize=1)
def load_model() -> tuple[Any, int]:
    """Load the model bundle and resolve the phishing probability column.

    The bundle is cached, so the model is read from disk only once per process.

    Returns:
        The fitted classifier and the index of the phishing class in
        ``predict_proba`` output.

    Raises:
        ModelNotFoundError: If the artifact file does not exist.
        FeatureMismatchError: If the stored feature order differs from the
            current one, which would silently produce wrong predictions.
    """
    if not MODEL_PATH.exists():
        raise ModelNotFoundError(
            f"Model artifact not found at {MODEL_PATH}. Run: python -m ml.train"
        )

    bundle = joblib.load(MODEL_PATH)
    classifier = bundle["classifier"]

    if tuple(bundle["feature_names"]) != FEATURE_NAMES:
        raise FeatureMismatchError(
            "Model was trained on a different feature set. Retrain with: "
            "python -m ml.train"
        )

    phishing_column = list(classifier.classes_).index(PHISHING_CLASS)
    return classifier, phishing_column


def classify_url(url: str, threshold: float = DEFAULT_THRESHOLD) -> Classification:
    """Classify a URL as phishing or legitimate.

    Only the hostname is analysed; the URL is never fetched.

    Args:
        url: Raw URL or bare hostname.
        threshold: Probability above which the URL is flagged as phishing.

    Returns:
        The classification result, including the phishing probability.
    """
    classifier, phishing_column = load_model()

    hostname = extract_hostname(url)
    vector = to_vector(extract_features(url))
    probability = float(classifier.predict_proba([vector])[0][phishing_column])

    return Classification(
        url=url,
        hostname=hostname,
        is_phishing=probability >= threshold,
        phishing_probability=probability,
    )