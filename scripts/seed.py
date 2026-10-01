"""Seed one admin and a minimal diagnostic catalogue."""

from sqlalchemy import select

from app.core.config import get_settings
from app.models.entities import Centre, CentreTest, DiagnosticTest, User
from app.services.auth import _password_hash
from app.db.session import get_session_factory


def _one(session: object, model: type[object], **filters: object) -> object | None:
    statement = select(model).filter_by(**filters)
    return session.scalar(statement)  # type: ignore[attr-defined]


def main() -> None:
    settings = get_settings()
    session = get_session_factory()()
    try:
        admin = _one(session, User, email=settings.seed_admin_email.strip().lower())
        if admin is None:
            admin = User(email=settings.seed_admin_email.strip().lower(), password_hash=_password_hash.hash(settings.seed_admin_password.get_secret_value()), role="ADMIN", is_active=True)
            session.add(admin)
        centre = _one(session, Centre, name="EVE Diagnostic Centre")
        if centre is None:
            centre = Centre(name="EVE Diagnostic Centre", location="Delhi", is_active=True); session.add(centre)
        test = _one(session, DiagnosticTest, name="Complete Blood Count")
        if test is None:
            test = DiagnosticTest(name="Complete Blood Count", description=None, is_active=True); session.add(test)
        session.flush()
        offering = session.scalar(select(CentreTest).where(CentreTest.centre_id == centre.id, CentreTest.test_id == test.id))
        if offering is None:
            offering = CentreTest(centre_id=centre.id, test_id=test.id, price_minor=49900, currency="INR", is_active=True); session.add(offering)
        session.commit()
        for label, record in (("admin", admin), ("centre", centre), ("test", test), ("offering", offering)):
            print(f"{label}_id={record.id}")
    except Exception:
        session.rollback(); raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
