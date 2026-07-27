"""One-off inspection: dataset shape, class balance, and label semantics."""

from ml.dataset import load_raw_dataset

KNOWN_LEGITIMATE_DOMAINS = ("google.com", "github.com", "wikipedia.org")


def main() -> None:
    frame = load_raw_dataset()
    print(f"rows: {len(frame)}")
    print(f"columns: {list(frame.columns)}")

    print("\nlabel counts:")
    print(frame["label"].value_counts())

    for label_value in sorted(frame["label"].unique()):
        print(f"\nsample URLs with label={label_value}:")
        for url in frame.loc[frame["label"] == label_value, "url"].head(5):
            print(f"  {url}")

    print("\nlabels for well-known legitimate domains:")
    for domain in KNOWN_LEGITIMATE_DOMAINS:
        matches = frame[frame["url"].str.contains(domain, na=False, regex=False)]
        if matches.empty:
            print(f"  {domain}: not found")
        else:
            print(f"  {domain}: {matches['label'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()