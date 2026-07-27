"""Check whether class separation comes from collection artifacts."""

import pandas as pd

from app.ml.features import extract_features
from ml.dataset import load_raw_dataset

SUSPECT_FEATURES = ["uses_https", "path_length", "url_length", "has_ip_host"]


def main() -> None:
    frame = load_raw_dataset()
    features = pd.DataFrame([extract_features(url) for url in frame["url"]])
    features["is_phishing"] = 1 - frame["label"]

    print("mean feature value per class:")
    print(features.groupby("is_phishing")[SUSPECT_FEATURES].mean())

    print("\npath_length distribution per class:")
    print(features.groupby("is_phishing")["path_length"].describe())

    empty_path_share = (
        features.assign(empty_path=features["path_length"] <= 1)
        .groupby("is_phishing")["empty_path"]
        .mean()
    )
    print("\nshare of URLs with empty path:")
    print(empty_path_share)


if __name__ == "__main__":
    main()