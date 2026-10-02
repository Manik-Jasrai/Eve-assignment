"""Application-level state values compatible with persisted text columns."""

from enum import StrEnum
from typing import Literal, TypeAlias


class BookingStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


TerminalPaymentStatus: TypeAlias = Literal[PaymentStatus.SUCCESS, PaymentStatus.FAILED]


class WebhookDisposition(StrEnum):
    APPLIED = "APPLIED"
    NOOP = "NOOP"
    DUPLICATE = "DUPLICATE"
