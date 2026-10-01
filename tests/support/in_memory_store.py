"""In-memory persistence double for HTTP tests."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from app.models.entities import Booking, Centre, CentreTest, DiagnosticTest, Payment, User, WebhookEvent


class InMemoryScalarResult:
    def __init__(self, records: list[object]) -> None:
        self._records = records

    def all(self) -> list[object]:
        return self._records


class InMemorySession:
    """Supports only persistence methods used by current API services."""

    def __init__(self) -> None:
        self._records: dict[type[object], dict[UUID, object]] = {
            User: {},
            Centre: {},
            DiagnosticTest: {},
            CentreTest: {},
            Booking: {},
            Payment: {}, WebhookEvent: {},
        }
        self._pending: object | None = None

    def add(self, entity: object) -> None:
        if getattr(entity, "id", None) is None:
            entity.id = uuid4()  # type: ignore[attr-defined]
        if getattr(entity, "created_at", None) is None:
            entity.created_at = datetime.now(UTC)  # type: ignore[attr-defined]
        self._pending = entity

    def commit(self) -> None:
        if self._pending is None:
            return
        if isinstance(self._pending, User) and any(
            isinstance(existing, User) and existing.email == self._pending.email
            for existing in self._records[User].values()
            if existing is not self._pending
        ):
            raise IntegrityError("insert users", {}, Exception("uq_users_email_normalized"))
        self._records[type(self._pending)][self._pending.id] = self._pending  # type: ignore[attr-defined]
        self._pending = None

    def refresh(self, entity: object) -> None:
        return None

    def rollback(self) -> None:
        self._pending = None

    def scalar(self, statement: object) -> User | None:
        parameters: dict[str, object] = statement.compile().params  # type: ignore[attr-defined]
        email = next((value for value in parameters.values() if isinstance(value, str)), None)
        return next(
            (
                user
                for user in self._records[User].values()
                if isinstance(user, User) and user.email == email
            ),
            None,
        )

    def scalars(self, statement: object) -> InMemoryScalarResult:
        model: type[object] = statement.column_descriptions[0]["type"]  # type: ignore[attr-defined]
        return InMemoryScalarResult(list(self._records[model].values()))

    def get(self, model: type[object], record_id: UUID) -> object | None:
        return self._records[model].get(record_id)

    def lock(self, model: type[object], record_id: UUID) -> object | None:
        return self.get(model, record_id)
