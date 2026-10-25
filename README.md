# Phishing Detector API

REST API that classifies URLs as phishing or legitimate using a scikit-learn
model trained on lexical hostname features, and explains whether an email looks
like phishing using retrieval-augmented generation (RAG) with Google Gemini.

## Problem

Phishing URLs are typically distributed faster than blocklists can be updated,
so a newly registered malicious domain is unknown to reputation services during
the window when it is most effective. This API scores an arbitrary URL on
demand from its structure alone — no lookup, no page fetch — and returns a
probability that a client application can act on with its own risk threshold.

On top of that score, `POST /analysis` takes the text of an email, scores every
hostname found in it, retrieves the most similar techniques from a curated
knowledge base, and asks an LLM to explain the evidence in plain language.

## Tech Stack

- **Language:** Python 3.12
- **Framework:** FastAPI
- **Database:** PostgreSQL 17 with pgvector (SQLAlchemy 2.0 ORM, Alembic migrations)
- **AI:** Google Gemini free tier (`google-genai`) for chat and embeddings
- **Key libraries:** scikit-learn, PyJWT, bcrypt, pydantic-settings, pytest
- **Tooling:** uv (dependency management), ruff (lint and formatting)
- **Containerization:** Docker / Docker Compose

## What This Demonstrates

- JWT authentication with bcrypt password hashing and route protection
- Schema evolution through reviewed Alembic migrations, including a column
  rename, a non-nullable foreign key, and a hand-written pgvector HNSW index
- Integration tests running against a real PostgreSQL instance, with each test
  rolled back through a savepoint-scoped session
- A machine learning pipeline where **data leakage was detected, diagnosed and
  corrected** — see [`docs/model.md`](docs/model.md)
- A RAG pipeline: embeddings, vector search with a distance cutoff, versioned
  prompts, and citation checking against the retrieved cases
- Defensive handling of an untrusted LLM input (the email) and of an external
  API (retries, clear 429/503 mapping, no internal details in error bodies)
- Multi-stage Docker build producing a runtime image without build tooling,
  training dependencies, or root privileges

## Architecture

```
                    ┌──────────────────────────────┐
  POST /predictions │  FastAPI                     │
  Bearer <token>    │                              │
  ────────────────► │  auth ──► JWT verification   │
                    │            │                 │
                    │            ▼                 │
                    │  features ──► hostname       │
                    │            │  extraction     │
                    │            ▼                 │
                    │  model ──► RandomForest      │
                    │            │  (in-memory,    │
                    │            │   cached)       │
                    │            ▼                 │
                    │  persist ──────────────────► │──► PostgreSQL
                    │            │                 │
  ◄──────────────── │  201 + probability           │
                    └──────────────────────────────┘

The analysed URL is never fetched. Features come from the string only.
```

Email analysis (`POST /analysis`):

```
email text
   │
   ├─► extract hostnames ──► classifier ──► score per hostname
   │
   ├─► Gemini embedding ──► pgvector search ──► closest cases (cutoff 0.39)
   │
   └─► prompt explain_email/v1 (email + scores + cases) ──► Gemini chat
                                   │
                                   ▼
          explanation + cited case slugs (only retrieved ones are kept)
                                   │
                                   ▼
        PostgreSQL: hash and metadata only, never the email or the explanation
```

The knowledge base is 27 curated markdown files in `knowledge/cases/`, each
describing one phishing technique, its warning signs and how to verify it.
Prompts live in `prompts/<name>/<version>/` and are never edited in place: a
change creates a new version, and the identifier (for example
`explain_email/v1`) is stored with every analysis.

## How to Run

```bash
git clone https://github.com/ArnaldSouza/phishing-detector-api.git
cd phishing-detector-api
cp .env.example .env
```

Fill in `.env`. The database and JWT variables are required, except the host and
port, which default to `localhost` and `5432`:

```
POSTGRES_USER=phishing_user
POSTGRES_PASSWORD=<choose one>
POSTGRES_DB=phishing_db
JWT_SECRET_KEY=<see below>
GEMINI_API_KEY=<free key from Google AI Studio>
```

On Windows, set `POSTGRES_HOST=127.0.0.1` instead of relying on the `localhost`
default: resolving `localhost` can add a delay of over a minute to the first
database connection (and to the test suite).

`GEMINI_API_KEY` is optional at startup: without it `/predictions` works and
`/analysis` answers `503`. Use the free tier without enabling billing.

Generate the signing key with a cryptographically secure source — never pick
one by hand:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Then:

```bash
docker compose up --build
```

The API waits for the database healthcheck, applies migrations, and starts on
`http://localhost:8000`. Interactive docs: `http://localhost:8000/docs`.

Load the knowledge base once (it uses a single embedding request):

```bash
docker compose exec api python -m scripts.ingest_cases
```

The step is idempotent, so running it again only updates the existing cases.
If it is skipped, analyses still work but run with no reference cases, and
nothing reports the problem.

## API Endpoints

| Method | Route            | Auth | Description                                  |
| ------ | ---------------- | ---- | -------------------------------------------- |
| POST   | `/auth/register` | —    | Create an account                            |
| POST   | `/auth/login`    | —    | Exchange credentials for a bearer token      |
| POST   | `/predictions`   | JWT  | Classify a URL and store the result          |
| POST   | `/analysis`      | JWT  | Explain whether an email looks like phishing |
| GET    | `/health`        | —    | Liveness check                               |
| GET    | `/health/db`     | —    | Database connectivity check                  |

Example request:

```bash
curl -X POST http://localhost:8000/predictions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "http://secure-login-paypal-verify.tk", "threshold": 0.5}'
```

```json
{
  "id": 3,
  "url": "http://secure-login-paypal-verify.tk",
  "hostname": "secure-login-paypal-verify.tk",
  "is_phishing": true,
  "phishing_probability": 0.909,
  "created_at": "2026-07-31T19:58:34.218495Z"
}
```

`threshold` is optional and defaults to `0.5`. Because the raw probability is
always returned, callers can trade recall against precision without the model
being retrained.

Email analysis (`email_text` accepts up to 10,000 characters):

```bash
curl -X POST http://localhost:8000/analysis \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email_text": "Dear customer, verify your identity within 24 hours at http://paypa1-secure-login.tk/verify or your account will be closed."}'
```

```json
{
  "id": 5,
  "explanation": "### Assessment\nThis email shows strong indicators of being a phishing attempt ... [urgency-account-suspension] ...\n\n### What to do next\n- **Do not click the link** ...",
  "signals": [
    { "hostname": "paypa1-secure-login.tk", "phishing_probability": 0.958 }
  ],
  "cited_slugs": ["urgency-account-suspension"],
  "prompt_identifier": "explain_email/v1",
  "model": "gemini-3.8-flash",
  "created_at": "2026-10-24T23:11:35.211657Z"
}
```

The explanation is shortened here. Errors from Gemini are mapped to `429` when
the free-tier rate limit is hit and to `503` for anything else.

## The Model

A random forest over 12 lexical features extracted from the hostname —
length, label count, digit ratio, Shannon entropy, TLD reputation, raw-IP and
punycode detection. Held-out accuracy is **0.86**, with 0.92 precision and 0.75
recall on the phishing class.

An earlier version reached 99.6% accuracy and was discarded: in the source
dataset every legitimate URL had an empty path and used HTTPS, so the model had
learned how the data was collected rather than what phishing looks like. The
investigation, the fix, and the remaining known biases are documented in
[`docs/model.md`](docs/model.md).

To retrain from scratch (downloads ~235k labelled URLs):

```bash
uv sync
uv run python -m ml.train
```

## Testing

Tests run against a real PostgreSQL instance rather than an in-memory
substitute, so that database constraints are actually exercised. Start the
database and create the test schema once:

```bash
docker compose up -d db
docker compose exec db psql -U phishing_user -d phishing_db \
  -c "CREATE DATABASE phishing_test_db;"
```

Then:

```bash
uv sync
uv run pytest
```

The suite has 192 tests and never calls Gemini: the chat and embedding calls
are replaced by fakes, so it needs no API key and spends no quota.

Covers: feature extraction invariants (including a regression test asserting
that path and scheme cannot influence the result), registration and login
flows, token rejection, user attribution of stored predictions, payload
validation, and the guarantee that failed logins do not reveal whether an email
is registered. For the AI layer: similarity ordering and the distance cutoff,
prompt building and delimiter escaping, citation filtering, the analysis
service (only a hash and metadata are stored, nothing is saved when Gemini
fails), and the router's 429/503 mapping, including that error bodies do not
leak configuration or the email text.

## Security Notes

- URLs are **never fetched**. Server-side retrieval of user-supplied URLs would
  expose the service to SSRF, allowing a caller to probe internal networks or
  cloud metadata endpoints through it. Hostnames found in emails are extracted
  from the text and scored the same way.
- Passwords are hashed with bcrypt and a per-password salt. Registration
  rejects inputs above bcrypt's 72-byte limit rather than silently truncating.
- Failed logins return an identical response whether the email is unknown or
  the password is wrong, so the endpoint cannot be used to enumerate accounts.
- The JWT algorithm is pinned at verification time, so a token declaring
  `alg: none` cannot bypass signature checking.
- `user_id` is taken from the verified token, never from the request body.
- The email is treated as untrusted input to the LLM (prompt injection). It is
  placed between `<email>` tags, any tag-like text inside it is escaped so it
  cannot close the block, and the prompt tells the model to treat it as data.
  This reduces the risk but does not remove it.
- The model may only cite cases that were retrieved; any other slug is dropped
  from the stored record. The prompt forbids declaring an email safe and
  forbids telling the user to open links or attachments.
- Only a SHA-256 hash and metadata of each analysis are stored, never the email
  text or the explanation.
- The Gemini key is read from the environment only. Error responses to clients
  are generic; details go to the server log.
- In the compose file the PostgreSQL port is bound to `127.0.0.1`, so the
  database is not reachable from the local network.

## Known Limitations

- **The email text is sent to Google** for embedding and for the explanation.
  On the free tier (unpaid quota), Google uses submitted content to improve its
  products and human reviewers may read it, and its terms say not to send
  sensitive, confidential or personal information. Do not submit real emails
  that contain other people's personal data. The terms also require users to be
  18 or older and, for users in the EEA, Switzerland or the UK, a paid service;
  see the [Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms).
- The retrieval cutoff (cosine distance 0.39) was set from a handful of sample
  emails, so treat it as a starting point rather than a calibrated value. A
  subtle phishing email with no urgency or links may fall outside the cutoff
  and get no reference cases, and an ordinary email can still get a cautious
  explanation.
- The explanation is generated text and can be wrong. It is a second opinion
  next to the classifier score, not a verdict.
- The knowledge base is loaded by a manual step (see How to Run). A fresh
  deployment without it still answers, but with no reference cases.
- A request holds a database connection while it waits for Gemini, which can
  take several seconds with retries. This is fine for a small service and would
  need a different session strategy under load.
- Registration is open and unthrottled, so anyone who registers can spend the
  Gemini free-tier quota; a production deployment would need rate limiting and
  email verification.
- Migrations are applied on container start for convenience. With multiple
  replicas this should be a separate job to avoid concurrent execution.
- Account registration returns `409` on a duplicate email, which does reveal
  that an address is in use. Avoiding this would require a confirmation-email
  flow.
- The classifier cannot detect phishing hosted on trusted infrastructure
  (`docs.google.com/forms/...`), and over-flags legitimate subdomains. Both are
  analysed in [`docs/model.md`](docs/model.md).

## License

MIT