"""Public catalogue reads and authenticated catalogue mutations."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models.entities import User
from app.dto.catalogue import CentreCreate, CentreDetail, CentreUpdate, DiagnosticTestCreate, DiagnosticTestDetail, DiagnosticTestUpdate, OfferingCreate, OfferingDetail, OfferingUpdate
from app.services import catalogue

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _page(items: list[object], limit: int, offset: int) -> dict[str, object]:
    return {"items": items, "limit": limit, "offset": offset}


@router.get("/centres/")
def centres(session: SessionDep, location: str | None = None, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)) -> dict[str, object]:
    items = [CentreDetail.model_validate(item) for item in catalogue.list_centres(session, location, limit, offset)]
    return _page(items, limit, offset)


@router.get("/centres/{centre_id}/", response_model=CentreDetail)
def centre(centre_id: UUID, session: SessionDep) -> object:
    return catalogue.get_centre(session, centre_id)


@router.post("/centres/", response_model=CentreDetail, status_code=status.HTTP_201_CREATED)
def create_centre(payload: CentreCreate, session: SessionDep, _user: CurrentUser) -> object:
    return catalogue.create_centre(session, payload.name, payload.location)


@router.patch("/centres/{centre_id}/", response_model=CentreDetail)
def patch_centre(centre_id: UUID, payload: CentreUpdate, session: SessionDep, _user: CurrentUser) -> object:
    return catalogue.update_centre(session, centre_id, payload.model_dump(exclude_unset=True))


@router.delete("/centres/{centre_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_centre(centre_id: UUID, session: SessionDep, _user: CurrentUser) -> Response:
    catalogue.deactivate_centre(session, centre_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/tests/")
def tests(session: SessionDep, name: str | None = None, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)) -> dict[str, object]:
    items = [DiagnosticTestDetail.model_validate(item) for item in catalogue.list_tests(session, name, limit, offset)]
    return _page(items, limit, offset)


@router.post("/tests/", response_model=DiagnosticTestDetail, status_code=status.HTTP_201_CREATED)
def create_test(payload: DiagnosticTestCreate, session: SessionDep, _user: CurrentUser) -> object:
    return catalogue.create_test(session, payload.name, payload.description)


@router.patch("/tests/{test_id}/", response_model=DiagnosticTestDetail)
def patch_test(test_id: UUID, payload: DiagnosticTestUpdate, session: SessionDep, _user: CurrentUser) -> object:
    return catalogue.update_test(session, test_id, payload.model_dump(exclude_unset=True))


@router.delete("/tests/{test_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_test(test_id: UUID, session: SessionDep, _user: CurrentUser) -> Response:
    catalogue.deactivate_test(session, test_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/centres/{centre_id}/tests/", response_model=list[OfferingDetail])
def offerings(centre_id: UUID, session: SessionDep) -> object:
    return catalogue.list_offerings(session, centre_id)


@router.post("/centres/{centre_id}/tests/", response_model=OfferingDetail, status_code=status.HTTP_201_CREATED)
def create_offering(centre_id: UUID, payload: OfferingCreate, session: SessionDep, _user: CurrentUser) -> object:
    return catalogue.create_offering(session, centre_id, payload.test_id, payload.price_minor)


@router.patch("/centres/{centre_id}/tests/{test_id}/", response_model=OfferingDetail)
def patch_offering(centre_id: UUID, test_id: UUID, payload: OfferingUpdate, session: SessionDep, _user: CurrentUser) -> object:
    return catalogue.update_offering(session, centre_id, test_id, payload.price_minor)


@router.delete("/centres/{centre_id}/tests/{test_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_offering(centre_id: UUID, test_id: UUID, session: SessionDep, _user: CurrentUser) -> Response:
    catalogue.deactivate_offering(session, centre_id, test_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
