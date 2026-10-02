# EVE Diagnostic Booking API

FastAPI backend for diagnostic-test discovery, booking, simulated payments, and idempotent payment webhooks.

## Run locally

Prerequisites: Python 3.12, Docker Desktop (for PostgreSQL), and a completed `.env` copied from `.env.example`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
docker compose up -d db
python -m alembic upgrade head
python -m scripts.seed
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`. Stop local containers with `docker compose down`; migrations are always explicit and never run during application startup.

Useful commands:

```bash
python -m pytest -q
python -m scripts.export_openapi
docker compose run --rm app alembic upgrade head
```

## API quickstart

| Area | Endpoints |
| --- | --- |
| Health | `GET /health/`, `/health/live/`, `/health/ready/` |
| Auth | `POST /auth/signup/`, `POST /auth/login/` |
| Catalogue | `GET /centres/`, `GET /tests/`, `GET /centres/{id}/tests/` plus authenticated create/update/deactivate routes |
| Bookings | `POST /bookings/`, `GET /bookings/`, `GET /bookings/{id}/` |
| Payments | `POST /payments/`, `GET /payments/{id}/`, `POST /payments/webhook/` |

```json
POST /auth/signup/
{"email":"patient@example.com","password":"correct-horse-battery"}
```

```json
POST /auth/login/
{"email":"patient@example.com","password":"correct-horse-battery"}
```

The seed command is safe to rerun and creates three correlated rows in every table: three users, centres, tests, offerings, bookings, payments, and webhook events. The configured `SEED_ADMIN_PASSWORD` is used for all three development users (`SEED_ADMIN_EMAIL`, `patient.one@example.com`, and `patient.two@example.com`).

Use the returned token as `Authorization: Bearer <access_token>`. After seeding, create a booking with one of the printed offering IDs:

```json
POST /bookings/
{"centre_test_id":"<offering-id>","appointment_at":"2030-12-01T10:00:00+05:30"}
```

```json
POST /payments/
{"booking_id":"<booking-id>"}
```

This creates a `PENDING` payment. The simulated provider completes it asynchronously through the webhook:

```json
POST /payments/webhook/
X-Webhook-Secret: <MOCK_WEBHOOK_SECRET>
{"event_id":"evt-demo-payment-001","payment_id":"<payment-id>","status":"SUCCESS","amount_minor":49900,"currency":"INR"}
```

## Database design

`users` own `bookings`; `centres` and `diagnostic_tests` connect through `centre_tests` offerings; bookings snapshot offering amount/currency; each booking has at most one `payment`; `webhook_events` records provider event IDs and payload hashes. Money uses integer INR paise. Catalogue deletion is soft deactivation, preserving booking history. Unique constraints protect normalized emails, test names, offerings, payments per booking, and processed webhook business payloads. Provider event IDs are retained as non-unique metadata.

## Assumptions

- Appointments must be future and timezone-aware; capacity allocation is not implemented.
- Any authenticated user currently manages catalogue data.
- Payment creation starts a local asynchronous simulation and copies values only from the booking snapshot.
- Secret-protected webhook callbacks provide the final `SUCCESS` or `FAILED` result and use durable payload-based deduplication.
- Automated tests use an in-memory database mock, not PostgreSQL.

## Future improvements

Use provider-signed callbacks with timestamps, background retries, refunds/cancellation, refresh/revocation, rate limits, capacity scheduling, PostgreSQL concurrency tests, and production monitoring.
