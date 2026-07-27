"""Train the phishing hostname classifier and persist the model bundle."""

from pathlib import Path
from typing import Final

import joblib
import numpy as np
import pandas as pd
import tldextract
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GroupShuffleSplit

from app.ml.features import FEATURE_NAMES, extract_features, extract_hostname, to_vector
from ml.dataset import load_raw_dataset

ARTIFACT_PATH: Final[Path] = Path(__file__).parent / "artifacts" / "classifier.joblib"
TEST_SIZE: Final[float] = 0.2
RANDOM_STATE: Final[int] = 42

_extract_domain = tldextract.TLDExtract(suffix_list_urls=())


def registrable_domain(hostname: str) -> str:
    """Return the registrable domain (eTLD+1) used to group hostnames."""
    parts = _extract_domain(hostname)
    return parts.top_domain_under_public_suffix or parts.domain or hostname


def build_hostname_dataset(frame: pd.DataFrame) -> pd.DataFrame:
    """Reduce raw URLs to one labelled row per hostname.

    Hostnames carrying both labels are dropped: at hostname granularity their
    class is genuinely undecidable, so keeping them would inject noise.

    Args:
        frame: DataFrame with ``url`` and PhiUSIIL ``label`` columns.

    Returns:
        DataFrame with unique ``hostname`` and ``is_phishing`` columns.
    """
    hosts = pd.DataFrame(
        {
            "hostname": frame["url"].map(extract_hostname),
            "is_phishing": 1 - frame["label"],
        }
    )
    hosts = hosts[hosts["hostname"] != ""]
    print(f"hostnames extracted: {len(hosts)}")

    distinct_labels = hosts.groupby("hostname")["is_phishing"].nunique()
    ambiguous = distinct_labels[distinct_labels > 1].index
    print(f"ambiguous hostnames dropped: {len(ambiguous)}")

    hosts = hosts[~hosts["hostname"].isin(ambiguous)]
    return hosts.drop_duplicates(subset="hostname").reset_index(drop=True)


def build_feature_matrix(hostnames: pd.Series) -> np.ndarray:
    """Convert hostnames into an ordered feature matrix."""
    return np.array([to_vector(extract_features(host)) for host in hostnames])


def split_by_domain(
    features: np.ndarray, labels: pd.Series, domains: pd.Series
) -> tuple[np.ndarray, np.ndarray, pd.Series, pd.Series]:
    """Split into train/test ensuring no domain appears in both sets."""
    splitter = GroupShuffleSplit(
        n_splits=1, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )
    train_index, test_index = next(splitter.split(features, labels, groups=domains))
    return (
        features[train_index],
        features[test_index],
        labels.iloc[train_index],
        labels.iloc[test_index],
    )


def train_classifier(features: np.ndarray, labels: pd.Series) -> RandomForestClassifier:
    """Fit a random forest on the extracted hostname features."""
    classifier = RandomForestClassifier(
        n_estimators=100,
        max_depth=16,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    classifier.fit(features, labels)
    return classifier


def report_performance(
    classifier: RandomForestClassifier, features: np.ndarray, labels: pd.Series
) -> None:
    """Print evaluation metrics and feature importances for the test set."""
    predictions = classifier.predict(features)

    print("\nclassification report:")
    print(
        classification_report(
            labels, predictions, target_names=["legitimate", "phishing"]
        )
    )

    print("confusion matrix (rows: actual, columns: predicted):")
    print(confusion_matrix(labels, predictions))

    print("\nfeature importances:")
    ranked = sorted(
        zip(FEATURE_NAMES, classifier.feature_importances_),
        key=lambda pair: pair[1],
        reverse=True,
    )
    for name, importance in ranked:
        print(f"  {name:<22} {importance:.4f}")


def save_bundle(classifier: RandomForestClassifier) -> None:
    """Persist the classifier together with the feature order it was trained on."""
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"classifier": classifier, "feature_names": FEATURE_NAMES},
        ARTIFACT_PATH,
        compress=3,
    )


def main() -> None:
    raw = load_raw_dataset()
    print(f"loaded {len(raw)} URLs")

    hosts = build_hostname_dataset(raw)
    print(f"unique hostnames kept: {len(hosts)}")
    print("\nclass balance:")
    print(hosts["is_phishing"].value_counts())

    domains = hosts["hostname"].map(registrable_domain)
    print(f"\nunique registrable domains: {domains.nunique()}")

    features = build_feature_matrix(hosts["hostname"])
    print(f"feature matrix: {features.shape}")

    train_features, test_features, train_labels, test_labels = split_by_domain(
        features, hosts["is_phishing"], domains
    )
    print(f"train: {len(train_labels)} | test: {len(test_labels)}")

    classifier = train_classifier(train_features, train_labels)
    report_performance(classifier, test_features, test_labels)

    save_bundle(classifier)
    print(f"\nmodel saved to {ARTIFACT_PATH}")


if __name__ == "__main__":
    main()