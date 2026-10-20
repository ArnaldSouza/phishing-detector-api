# Phishing Detector API

REST API that classifies URLs as phishing or legitimate using a scikit-learn
model trained on lexical hostname features.

## Problem

Phishing URLs are typically distributed faster than blocklists can be updated,
so a newly registered malicious domain is unknown to reputation services during
the window when it is most effective. This API scores an arbitrary URL on
demand from its structure alone — no lookup, no page fetch — and returns a
probability that a client application can act on with its own risk threshold.

## Tech Stack

- **Language:** Python 3.12
- **Framework:** FastAPI
- **Database:** PostgreSQL 17 (SQLAlchemy 2.0 ORM, Alembic migrations)
- **Key libraries:** scikit-learn, PyJWT, bcrypt, pydantic-settings, pytest
- **Tooling:** uv (dependency management), ruff (lint and formatting)
- **Containerization:** Docker / Docker Compose

## What This Demonstrates

- JWT authentication with bcrypt password hashing and route protection
- Schema evolution through reviewed Alembic migrations, including a column
  rename and the introduction of a non-nullable foreign key
- Integration tests running against a real PostgreSQL instance, with each test
  rolled back through a savepoint-scoped session
- A machine learning pipeline where **data leakage was detected, diagnosed and
  corrected** — see [`docs/model.md`](docs/model.md)
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

## How to Run

```bash
git clone https://github.com/ArnaldSouza/phishing-detector-api.git
cd phishing-detector-api
cp .env.example .env
```

Fill in `.env`. Every variable is required except the host and port, which
default to `localhost` and `5432`:

```
POSTGRES_USER=phishing_user
POSTGRES_PASSWORD=<choose one>
POSTGRES_DB=phishing_db
JWT_SECRET_KEY=<see below>
```

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

## API Endpoints

| Method | Route            | Auth | Description                             |
| ------ | ---------------- | ---- | --------------------------------------- |
| POST   | `/auth/register` | —    | Create an account                       |
| POST   | `/auth/login`    | —    | Exchange credentials for a bearer token |
| POST   | `/predictions`   | JWT  | Classify a URL and store the result     |
| GET    | `/health`        | —    | Liveness check                          |
| GET    | `/health/db`     | —    | Database connectivity check             |

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

Covers: feature extraction invariants (including a regression test asserting
that path and scheme cannot influence the result), registration and login
flows, token rejection, user attribution of stored predictions, payload
validation, and the guarantee that failed logins do not reveal whether an email
is registered.

## Security Notes

- URLs are **never fetched**. Server-side retrieval of user-supplied URLs would
  expose the service to SSRF, allowing a caller to probe internal networks or
  cloud metadata endpoints through it.
- Passwords are hashed with bcrypt and a per-password salt. Registration
  rejects inputs above bcrypt's 72-byte limit rather than silently truncating.
- Failed logins return an identical response whether the email is unknown or
  the password is wrong, so the endpoint cannot be used to enumerate accounts.
- The JWT algorithm is pinned at verification time, so a token declaring
  `alg: none` cannot bypass signature checking.
- `user_id` is taken from the verified token, never from the request body.

## Known Limitations

- Registration is open and unthrottled; a production deployment would need rate
  limiting and email verification.
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
