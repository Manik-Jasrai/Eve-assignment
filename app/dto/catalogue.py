"""DTOs for the public diagnostic catalogue."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator


Name = Annotated[str, Field(min_length=1, max_length=150)]
Location = Annotated[str, Field(min_length=1, max_length=250)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


def _trim(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be blank")
    return value


class CentreCreate(StrictModel):
    name: Name
    location: Location

    _trim_name = field_validator("name")(_trim)
    _trim_location = field_validator("location")(_trim)


class CentreUpdate(StrictModel):
    name: Name | None = None
    location: Location | None = None

    _trim_name = field_validator("name")(_trim)
    _trim_location = field_validator("location")(_trim)

    @model_validator(mode="after")
    def has_update(self) -> "CentreUpdate":
        if self.name is None and self.location is None:
            raise ValueError("at least one field is required")
        return self


class CentreDetail(StrictModel):
    id: UUID
    name: str
    location: str
    is_active: bool


class DiagnosticTestCreate(StrictModel):
    name: Name
    description: Annotated[str | None, Field(max_length=2000)] = None

    _trim_name = field_validator("name")(_trim)


class DiagnosticTestUpdate(StrictModel):
    name: Name | None = None
    description: Annotated[str | None, Field(max_length=2000)] = None

    _trim_name = field_validator("name")(_trim)

    @model_validator(mode="after")
    def has_update(self) -> "DiagnosticTestUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field is required")
        return self


class DiagnosticTestDetail(StrictModel):
    id: UUID
    name: str
    description: str | None
    is_active: bool


class OfferingCreate(StrictModel):
    test_id: UUID
    price_minor: Annotated[StrictInt, Field(gt=0)]


class OfferingUpdate(StrictModel):
    price_minor: Annotated[StrictInt, Field(gt=0)]


class OfferingDetail(StrictModel):
    id: UUID
    centre_id: UUID
    test_id: UUID
    price_minor: int
    currency: str
    is_active: bool


class Page(BaseModel):
    items: list[object]
    limit: int
    offset: int
