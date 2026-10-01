# EVE Healthcare Backend Assignment

This submission is a FastAPI service for diagnostic-centre catalogues, authenticated test bookings, simulated payments, and idempotent payment webhooks.

Highlights:

- Argon2-backed email/password authentication with JWT bearer tokens.
- Public diagnostic catalogue and authenticated catalogue management.
- Owner-scoped bookings that snapshot INR paise pricing.
- Simulated `SUCCESS`/`FAILED` payments with booking-state transitions.
- Secret-authenticated, idempotent webhooks using event IDs and payload hashes.
- PostgreSQL/Alembic schema, Docker Compose setup, OpenAPI export, and in-memory unit/integration tests.

Run locally using the Bash setup in [README.md](README.md). The test suite runs with:

```bash
python -m pytest -q
```

Current result: 24 passing tests.
