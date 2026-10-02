# EVE Repository Agent Guide

## Project description

EVE is a Python 3.12 and FastAPI backend for booking diagnostic tests. It uses
Pydantic for API schemas, SQLAlchemy for persistence, Alembic for database
migrations, and PostgreSQL as its database. The application includes
authentication, diagnostic-centre and test catalogue management, booking and
mock-payment workflows, idempotent webhook handling, structured logging, and
health/readiness endpoints.

The implementation and operating instructions are documented in `README.md`.
Read the relevant documentation before changing behavior or making
architectural decisions.

## Repository structure

- `app/api/`: route composition, request dependencies, and HTTP handlers.
- `app/dto/`: Pydantic request and response models.
- `app/services/`: business workflows and transaction boundaries.
- `app/models/`: SQLAlchemy domain entities.
- `app/db/`: database sessions, metadata, and readiness checks.
- `app/core/`: configuration, errors, middleware, and logging.
- `app/integrations/`: adapters for external or simulated systems.
- `migrations/`: Alembic configuration and versioned schema changes.
- `tests/`: unit and integration tests mirroring application behavior.
- `scripts/`: operational and development scripts.

Respect these boundaries. Add new code to the most specific existing module;
create a focused module when no suitable one exists.

## Code quality principles

- Prefer clear, explicit code over clever abstractions.
- Keep route handlers thin. Put business rules and transaction orchestration in
  services, validation and serialization in schemas, and persistence concerns
  in database or model modules.
- Follow the single-responsibility principle. Split large workflows into small,
  named helper functions and cohesive modules instead of placing unrelated
  behavior in one function or file.
- Avoid premature frameworks and generic repository layers. Reuse a helper only
  when it represents a real, repeated concept.
- Use precise names, type hints, and short docstrings where intent is not obvious.
- Preserve the established async/sync style, error format, logging conventions,
  dependency-injection pattern, and API contract.
- Keep secrets and environment-specific values out of source code. Add safe
  examples to `.env.example` when introducing configuration.
- Treat money, timestamps, authentication, authorization, state transitions,
  transactions, and webhook idempotency as correctness-sensitive concerns.
- Make database changes through an Alembic migration and keep ORM models aligned
  with the schema.
- Add or update focused tests for every behavior change and regression fix.

## Rules for agents

1. Inspect the relevant implementation, tests, and documentation before
   editing. Do not guess at repository conventions.
2. Preserve the repository structure and public contracts unless the task
   explicitly requires a change. Keep changes narrowly scoped to the request.
3. Do not put everything in one function or file. Extract helpers for distinct
   responsibilities and place reusable behavior in the appropriate module.
4. Do not overwrite, revert, or reformat unrelated user changes. Never commit
   secrets, generated caches, virtual environments, or local configuration.
5. Before running any test, linter, formatter, type checker, migration check, or
   other validation command, show the current diff to the user. If further edits
   are made, show the updated diff again before running more validation.
6. Run the smallest relevant validation first, then broaden it when warranted.
   The standard test command is `py -m pytest`.
7. Do not weaken or delete a test merely to make a change pass. Fix the behavior
   or explain why the expected behavior must intentionally change.
8. Keep API errors safe and consistent. Do not expose credentials, tokens,
   password hashes, stack traces, or internal database details.
9. Use structured logging and avoid logging sensitive data. Preserve request IDs
   and useful operational context.
10. For schema or workflow changes, consider rollback behavior, concurrency,
    idempotency, and partial failures before implementation.
11. Update documentation and examples when commands, configuration, API
    contracts, or architectural decisions change.
12. At handoff, summarize the files changed, the behavior affected, the diff
    reviewed, and the validation performed. Clearly report any validation that
    was skipped or could not run.
13. Do not use any type, maintain typesafety everywhere. Declare type everywhere.
14. We are using an in-memory db for test just to mock the DB for easier testing
