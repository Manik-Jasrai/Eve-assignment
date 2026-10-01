"""Catalogue business rules and synchronous persistence operations."""

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models.entities import Centre, CentreTest, DiagnosticTest


def _all(session: Session, model: type[Centre] | type[DiagnosticTest] | type[CentreTest]) -> list[object]:
    return list(session.scalars(select(model)).all())


def _commit(session: Session, entity: object) -> object:
    session.add(entity)
    session.commit()
    session.refresh(entity)
    return entity


def _active(entity: Centre | DiagnosticTest | CentreTest | None, message: str = "Resource not found") -> object:
    if entity is None:
        raise NotFoundError(message)
    if not entity.is_active:
        raise ConflictError("Resource is inactive")
    return entity


def list_centres(session: Session, location: str | None, limit: int, offset: int) -> list[Centre]:
    items = [item for item in _all(session, Centre) if isinstance(item, Centre) and item.is_active]
    if location:
        needle = location.strip().lower()
        items = [item for item in items if needle in item.location.lower()]
    return sorted(items, key=lambda item: (item.name.lower(), str(item.id)))[offset : offset + limit]


def create_centre(session: Session, name: str, location: str) -> Centre:
    return _commit(session, Centre(name=name, location=location, is_active=True))  # type: ignore[return-value]


def get_centre(session: Session, centre_id: UUID, *, writable: bool = False) -> Centre:
    centre = session.get(Centre, centre_id)
    if centre is None:
        raise NotFoundError("Centre not found")
    if not centre.is_active:
        if writable:
            raise ConflictError("Centre is inactive")
        raise NotFoundError("Centre not found")
    return centre


def update_centre(session: Session, centre_id: UUID, changes: dict[str, object]) -> Centre:
    centre = get_centre(session, centre_id, writable=True)
    for field, value in changes.items():
        setattr(centre, field, value)
    return _commit(session, centre)  # type: ignore[return-value]


def deactivate_centre(session: Session, centre_id: UUID) -> None:
    centre = session.get(Centre, centre_id)
    if centre is None:
        raise NotFoundError("Centre not found")
    if centre.is_active:
        centre.is_active = False
        _commit(session, centre)


def list_tests(session: Session, name: str | None, limit: int, offset: int) -> list[DiagnosticTest]:
    items = [item for item in _all(session, DiagnosticTest) if isinstance(item, DiagnosticTest) and item.is_active]
    if name:
        needle = name.strip().lower()
        items = [item for item in items if needle in item.name.lower()]
    return sorted(items, key=lambda item: (item.name.lower(), str(item.id)))[offset : offset + limit]


def create_test(session: Session, name: str, description: str | None) -> DiagnosticTest:
    if any(item.name.lower() == name.lower() for item in _all(session, DiagnosticTest) if isinstance(item, DiagnosticTest)):
        raise ConflictError("A diagnostic test with this name already exists")
    return _commit(session, DiagnosticTest(name=name, description=description, is_active=True))  # type: ignore[return-value]


def _get_test(session: Session, test_id: UUID, *, writable: bool = False) -> DiagnosticTest:
    test = session.get(DiagnosticTest, test_id)
    if test is None:
        raise NotFoundError("Diagnostic test not found")
    if not test.is_active:
        if writable:
            raise ConflictError("Diagnostic test is inactive")
        raise NotFoundError("Diagnostic test not found")
    return test


def update_test(session: Session, test_id: UUID, changes: dict[str, object]) -> DiagnosticTest:
    test = _get_test(session, test_id, writable=True)
    for field, value in changes.items():
        setattr(test, field, value)
    return _commit(session, test)  # type: ignore[return-value]


def deactivate_test(session: Session, test_id: UUID) -> None:
    test = session.get(DiagnosticTest, test_id)
    if test is None:
        raise NotFoundError("Diagnostic test not found")
    if test.is_active:
        test.is_active = False
        _commit(session, test)


def list_offerings(session: Session, centre_id: UUID) -> list[CentreTest]:
    get_centre(session, centre_id)
    active_tests = {item.id for item in _all(session, DiagnosticTest) if isinstance(item, DiagnosticTest) and item.is_active}
    return [item for item in _all(session, CentreTest) if isinstance(item, CentreTest) and item.centre_id == centre_id and item.is_active and item.test_id in active_tests]


def create_offering(session: Session, centre_id: UUID, test_id: UUID, price_minor: int) -> CentreTest:
    get_centre(session, centre_id, writable=True)
    _get_test(session, test_id, writable=True)
    if any(item.centre_id == centre_id and item.test_id == test_id for item in _all(session, CentreTest) if isinstance(item, CentreTest)):
        raise ConflictError("Offering already exists")
    return _commit(session, CentreTest(centre_id=centre_id, test_id=test_id, price_minor=price_minor, currency="INR", is_active=True))  # type: ignore[return-value]


def _get_offering(session: Session, centre_id: UUID, test_id: UUID, *, writable: bool) -> CentreTest:
    get_centre(session, centre_id, writable=writable)
    offering = next((item for item in _all(session, CentreTest) if isinstance(item, CentreTest) and item.centre_id == centre_id and item.test_id == test_id), None)
    if offering is None:
        raise NotFoundError("Offering not found")
    if not offering.is_active:
        raise ConflictError("Offering is inactive")
    return offering


def update_offering(session: Session, centre_id: UUID, test_id: UUID, price_minor: int) -> CentreTest:
    offering = _get_offering(session, centre_id, test_id, writable=True)
    offering.price_minor = price_minor
    return _commit(session, offering)  # type: ignore[return-value]


def deactivate_offering(session: Session, centre_id: UUID, test_id: UUID) -> None:
    offering = _get_offering(session, centre_id, test_id, writable=True)
    offering.is_active = False
    _commit(session, offering)
