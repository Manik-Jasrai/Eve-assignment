"""Public authentication routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models.entities import User
from app.dto.auth import AuthCredentials, SignupResponse, TokenResponse
from app.services.auth import authenticate_user, create_access_token, register_user

router = APIRouter(prefix="/auth")

@router.post("/signup/", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(
    credentials: AuthCredentials,
    session: Annotated[Session, Depends(get_db_session)],
) -> SignupResponse:
    """Register one new account for an email address."""
    user = register_user(session, email=str(credentials.email), password=credentials.password)
    return SignupResponse(id=user.id, email=user.email)


@router.post("/login/", response_model=TokenResponse)
def login(
    credentials: AuthCredentials,
    session: Annotated[Session, Depends(get_db_session)],
) -> TokenResponse:
    """Authenticate credentials and return a signed bearer token."""
    user = authenticate_user(session, email=str(credentials.email), password=credentials.password)
    token, expires_in = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/secret/")
def secret(
    _current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    """Demonstrate an endpoint that requires a valid bearer token."""
    return {"message": "Authenticated access granted"}
