"""Mock payment and webhook endpoints."""
import hmac
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.errors import AuthenticationError
from app.db.session import get_db_session
from app.dto.payments import PaymentCreate, PaymentDetail, WebhookRequest, WebhookResponse
from app.models.entities import User
from app.services import payments
router = APIRouter(prefix="/payments")
SessionDep = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
@router.post("/", response_model=PaymentDetail)
def create(payload: PaymentCreate, session: SessionDep, user: CurrentUser, response: Response) -> PaymentDetail:
    payment, created = payments.finalize(session, user.id, payload.booking_id, payload.simulate_status)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return PaymentDetail.model_validate(payment)
@router.get("/{payment_id}/", response_model=PaymentDetail)
def detail(payment_id: UUID, session: SessionDep, user: CurrentUser) -> PaymentDetail: return PaymentDetail.model_validate(payments.get_payment(session, user.id, payment_id))
@router.post("/webhook/", response_model=WebhookResponse)
def webhook(payload: WebhookRequest, session: SessionDep, x_webhook_secret: Annotated[str | None, Header()] = None) -> WebhookResponse:
    if x_webhook_secret is None or not hmac.compare_digest(x_webhook_secret, get_settings().mock_webhook_secret.get_secret_value()): raise AuthenticationError("Invalid webhook secret")
    return WebhookResponse(payment_id=payload.payment_id, disposition=payments.handle_webhook(session, payload.event_id, payload.payment_id, payload.status, payload.amount_minor, payload.currency))
