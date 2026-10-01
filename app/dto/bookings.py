"""Booking request and response DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.states import BookingStatus


class BookingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    centre_test_id: UUID
    appointment_at: datetime

    @field_validator("appointment_at")
    @classmethod
    def requires_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("appointment_at must include a timezone")
        return value


class BookingDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    centre_test_id: UUID
    centre_id: UUID
    test_id: UUID
    appointment_at: datetime
    amount_minor: int
    currency: str
    status: BookingStatus
