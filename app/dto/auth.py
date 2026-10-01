"""Request and response models for email/password authentication."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator


Password = Annotated[str, StringConstraints(min_length=12, max_length=128)]


class AuthCredentials(BaseModel):
    """Strict credentials accepted by signup and login."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: Password

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class SignupResponse(BaseModel):
    """Safe representation of a newly registered user."""

    id: UUID
    email: EmailStr


class TokenResponse(BaseModel):
    """Bearer token returned after a successful login."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(gt=0)
