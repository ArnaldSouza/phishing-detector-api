# Model Notes

Documentation of the phishing classifier: data, methodology, performance,
and known limitations.

## Dataset

[PhiUSIIL Phishing URL Dataset](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset)
(UCI Machine Learning Repository, CC BY 4.0) — 235,795 labelled URLs.

Only the `URL` and `label` columns are used. The dataset ships with dozens of
pre-computed features, all discarded: feature extraction is part of this
project and reusing them would bypass it.

Note: PhiUSIIL labels `1` as legitimate and `0` as phishing, inverting the more
common convention. Labels are flipped at load time so that `1` means phishing
throughout the codebase, matching the `is_phishing` column in the database.

## Leakage found in the raw dataset

An initial model trained on full-URL features reached 99.6% accuracy. Per-class
feature analysis showed why:

| Feature       | Legitimate     | Phishing    |
| ------------- | -------------- | ----------- |
| `path_length` | 0.0 (max: 0.0) | 8.7 average |
| `uses_https`  | 1.000          | 0.487       |

All 134,850 legitimate URLs had an empty path and used HTTPS — without a single
exception. The two classes were separable by a deterministic rule.

This reflects **how the dataset was collected**, not what phishing looks like:
legitimate samples were gathered as bare home pages, phishing samples as full
attack URLs. A model trained on this learns the collection process. In
production it would flag any legitimate URL with a path, and miss any phishing
URL served over HTTPS — which most are, since certificates are free.

## Design decisions

**Hostname-only features.** Scheme and path are discarded entirely. Both classes
are then observed through the same lens, removing the artifact at its root.
Enforced by a regression test asserting that path and scheme cannot change the
extracted features.

**Leading `www.` stripped.** Legitimate samples were overwhelmingly `www.`-prefixed
while phishing samples were not — a second collection artifact, neutralised
before it could become signal.

**Deduplication by hostname.** Once features derive from the hostname alone,
many URLs collapse into identical rows. Duplicates are removed so no host is
weighted by how often it was crawled.

**Ambiguous hostnames dropped** (58 rows). Hosts carrying both labels — abused
shared services — have no decidable class at hostname granularity.

**Train/test split grouped by registrable domain** (eTLD+1, resolved via the
Public Suffix List). Without grouping, `evil.tk/a` in train and `evil.tk/b` in
test would let the model score well by memorising domains.

## Performance

Random forest, 100 trees, evaluated on 47,774 held-out hostnames.

| Class      | Precision | Recall | F1   |
| ---------- | --------- | ------ | ---- |
| Legitimate | 0.83      | 0.95   | 0.88 |
| Phishing   | 0.92      | 0.75   | 0.82 |

Accuracy: 0.86.

The model is conservative: it misses roughly a quarter of phishing hostnames,
but is right 92% of the time when it does flag one. The API returns the raw
probability alongside the verdict so the decision threshold can be tuned by the
consumer.

Top features by importance: `hostname_length` (0.196), `num_labels` (0.153),
`has_suspicious_tld` (0.138), `tld_length` (0.095).

## Known limitations

**Legitimate subdomains are over-flagged.** `docs.google.com` scores 0.753 and is
classified as phishing at the default threshold. The legitimate samples were
collected as apex domains, so legitimate subdomains are under-represented, while
phishing samples frequently use free hosting subdomains
(`*.firebaseapp.com`, `*.xsph.ru`). `num_labels` therefore carries residual
collection bias. The signal is not purely artificial — free hosting abuse is
real — but the effect is overstated.

**Abuse of trusted services is invisible.** A phishing page hosted at
`docs.google.com/forms/d/e/1FAIpQLSc...` is indistinguishable from a legitimate
one by hostname. Lexical features cannot detect this class of attack; it would
require path analysis, reputation data, or page content.

**Suspicious TLD list is a hardcoded prior.** `SUSPICIOUS_TLDS` encodes domain
knowledge that will go stale as abuse patterns shift. It is not learned from
data and should be revisited periodically.

**Rare features score low on importance, not on usefulness.** `has_ip_host`
ranks last (0.0002) because raw-IP hosts are rare after deduplication, yet
`43.134.167.94` scores 0.992. Gini importance weights by sample count, so a
decisive but infrequent feature looks negligible.

## Security note

URLs are never fetched. All features are computed from the string alone.
Fetching user-supplied URLs server-side would expose the API to SSRF, letting a
caller probe internal networks or cloud metadata endpoints
(e.g. `http://169.254.169.254/`) through the service.