# EVE Healthcare Backend Assignment

This submission implements a FastAPI backend for diagnostic-test discovery, authenticated bookings, simulated payments, and idempotent payment webhooks.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
docker compose up -d db
python -m alembic upgrade head
python -m scripts.seed
python -m uvicorn app.main:app --reload
```

Swagger UI is available at `http://127.0.0.1:8000/docs`. Run the in-memory test suite with:

```bash
python -m pytest -q
```

## Key points

- Argon2 password hashing and JWT bearer authentication.
- Diagnostic-centre, diagnostic-test, and offering catalogue APIs.
- Authenticated bookings with server-side INR-paise price snapshots.
- Simulated `SUCCESS` and `FAILED` payment processing with booking-state transitions.
- Secret-protected, idempotent webhooks using provider event IDs and payload hashes.
- PostgreSQL/Alembic schema migrations, Docker Compose, OpenAPI export, and 24 passing tests.

## Assumptions

- Appointments must be future and timezone-aware; capacity scheduling is out of scope.
- Any authenticated user can currently manage catalogue data.
- Payments are synchronous mock simulations rather than a real provider integration.
- Catalogue deletion is soft deactivation to preserve booking history.
- Tests use an in-memory database mock; PostgreSQL is used for production/runtime configuration.
