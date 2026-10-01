"""Pure deterministic payment-provider simulation."""

from app.core.errors import BusinessRuleError
from app.core.states import PaymentStatus


def simulate_result(result: PaymentStatus | str) -> PaymentStatus:
    """Return a requested terminal result without network activity."""
    try:
        status = PaymentStatus(result)
    except ValueError as exc:
        raise BusinessRuleError("simulate_status must be SUCCESS or FAILED") from exc
    if status is PaymentStatus.PENDING:
        raise BusinessRuleError("simulate_status must be SUCCESS or FAILED")
    return status
