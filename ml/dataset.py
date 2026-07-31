"""Download and cache the PhiUSIIL phishing URL dataset."""

from pathlib import Path

import pandas as pd
from ucimlrepo import fetch_ucirepo

PHIUSIIL_REPO_ID = 967
_CACHE_PATH = Path(__file__).parent / "data" / "phiusiil_raw.csv"


def load_raw_dataset(refresh: bool = False) -> pd.DataFrame:
    """Load the PhiUSIIL dataset keeping only the URL and label columns.

    The dataset is downloaded once and cached locally as CSV.

    Args:
        refresh: When True, ignore the local cache and download again.

    Returns:
        DataFrame with columns ``url`` and ``label``.
    """
    if _CACHE_PATH.exists() and not refresh:
        return pd.read_csv(_CACHE_PATH)

    dataset = fetch_ucirepo(id=PHIUSIIL_REPO_ID)
    frame = pd.concat([dataset.data.features, dataset.data.targets], axis=1)
    frame = frame[["URL", "label"]].rename(columns={"URL": "url"})

    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(_CACHE_PATH, index=False)
    return frame
