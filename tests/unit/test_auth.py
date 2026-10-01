"""Unit coverage for the minimal authentication primitives."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from pydantic import SecretStr, ValidationError

from app.core.errors import AuthenticationError
from app.dto.auth import AuthCredentials
from app.services.auth import create_access_token, decode_subject, get_authenticated_user


@pytest.fixture
def settings() -> SimpleNamespace:
    return SimpleNamespace(
        jwt_secret=SecretStr("unit-test-secret"),
        jwt_issuer="eve-tests",
        jwt_audience="eve-test-clients",
        jwt_expire_minutes=30,
    )


def test_credentials_normalize_email_and_preserve_password() -> None:
    credentials = AuthCredentials(email=" User@Example.COM ", password="  password-is-unchanged  ")

    assert credentials.email == "user@example.com"
    assert credentials.password == "  password-is-unchanged  "


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": "long-enough-password"},
        {"email": "user@example.com", "password": "too-short"},
        {"email": "user@example.com", "password": "x" * 129},
        {"email": "user@example.com", "password": "long-enough-password", "role": "ADMIN"},
    ],
)
def test_credentials_reject_invalid_or_extra_input(payload: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        AuthCredentials.model_validate(payload)


def test_access_token_round_trip(settings: SimpleNamespace) -> None:
    user_id = uuid4()
    token, expires_in = create_access_token(user_id, settings)

    assert expires_in == 1800
    assert decode_subject(token, settings) == user_id


@pytest.mark.parametrize(
    "claims",
    [
        {"iss": "wrong-issuer"},
        {"aud": "wrong-audience"},
        {"exp": datetime.now(UTC) - timedelta(seconds=1)},
        {"sub": "not-a-uuid"},
    ],
)
def test_access_token_rejects_invalid_claims(settings: SimpleNamespace, claims: dict[str, object]) -> None:
    now = datetime.now(UTC)
    payload = {
        "sub": str(uuid4()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + timedelta(minutes=1),
    }
    payload.update(claims)
    token = jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm="HS256")

    with pytest.raises(AuthenticationError):
        decode_subject(token, settings)


def test_access_token_rejects_wrong_algorithm(settings: SimpleNamespace) -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(minutes=1),
        },
        "different-secret",
        algorithm="HS384",
    )

    with pytest.raises(AuthenticationError):
        decode_subject(token, settings)


def test_current_user_requires_a_persisted_subject() -> None:
    class EmptySession:
        def get(self, model: object, user_id: object) -> None:
            return None

    with pytest.raises(AuthenticationError):
        get_authenticated_user(EmptySession(), uuid4())  # type: ignore[arg-type]
