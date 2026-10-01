"""Payment and webhook DTOs."""
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from app.core.states import PaymentStatus

class PaymentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    booking_id: UUID
    simulate_status: PaymentStatus

class PaymentDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    booking_id: UUID
    amount_minor: int
    currency: str
    status: PaymentStatus

class WebhookRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "event_id": "evt-demo-payment-001",
                "payment_id": "11111111-1111-4111-8111-111111111111",
                "status": "SUCCESS",
                "amount_minor": 49900,
                "currency": "INR",
            }
        },
    )
    event_id: str = Field(min_length=1, max_length=100, examples=["evt-demo-payment-001"])
    payment_id: UUID = Field(examples=["11111111-1111-4111-8111-111111111111"])
    status: PaymentStatus = Field(examples=["SUCCESS"])
    amount_minor: StrictInt = Field(gt=0, examples=[49900])
    currency: str = Field(pattern="^INR$", examples=["INR"])

class WebhookResponse(BaseModel):
    payment_id: UUID
    disposition: str
