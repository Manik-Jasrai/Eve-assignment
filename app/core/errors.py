"""API error types and exception handler registration."""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)


class ErrorDetail(BaseModel):
    field: str | None = None
    reason: str


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorBody


class DomainError(Exception):
    """Expected domain failure rendered through the standard error envelope."""

    def __init__(self, status_code: int, code: str, message: str, details: list[ErrorDetail] | None = None) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []


class AuthenticationError(DomainError):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(HTTP_401_UNAUTHORIZED, "AUTHENTICATION_FAILED", message)


class AuthorizationError(DomainError):
    def __init__(self, message: str = "You are not allowed to perform this action") -> None:
        super().__init__(HTTP_403_FORBIDDEN, "AUTHORIZATION_FAILED", message)


class NotFoundError(DomainError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(HTTP_404_NOT_FOUND, "NOT_FOUND", message)


class ConflictError(DomainError):
    def __init__(self, message: str = "Resource state conflicts with this request") -> None:
        super().__init__(HTTP_409_CONFLICT, "CONFLICT", message)


class BusinessRuleError(DomainError):
    def __init__(self, message: str, details: list[ErrorDetail] | None = None) -> None:
        super().__init__(HTTP_422_UNPROCESSABLE_ENTITY, "BUSINESS_RULE_VIOLATION", message, details)


class ServiceUnavailableError(DomainError):
    def __init__(self, message: str = "Service is temporarily unavailable") -> None:
        super().__init__(HTTP_503_SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE", message)


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[ErrorDetail] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    response = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            request_id=request_id,
            details=details or [],
        )
    )
    return JSONResponse(status_code=status_code, content=response.model_dump())


def _safe_validation_details(errors: list[dict[str, Any]]) -> list[ErrorDetail]:
    """Expose field paths and messages, but never rejected raw values."""
    return [
        ErrorDetail(field=".".join(map(str, error["loc"])), reason=error["msg"])
        for error in errors
    ]


def register_exception_handlers(app: FastAPI) -> None:
    """Register API-wide handlers for expected and unexpected failures."""

    @app.exception_handler(DomainError)
    def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        response = _error_response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )
        if exc.status_code == HTTP_401_UNAUTHORIZED:
            response.headers["WWW-Authenticate"] = "Bearer"
        return response

    @app.exception_handler(RequestValidationError)
    def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error_response(
            request,
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details=_safe_validation_details(exc.errors()),
        )

    @app.exception_handler(HTTPException)
    def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
        response = _error_response(
            request,
            status_code=exc.status_code,
            code="HTTP_ERROR",
            message=detail,
        )
        if exc.status_code == HTTP_401_UNAUTHORIZED:
            response.headers["WWW-Authenticate"] = "Bearer"
        return response

    @app.exception_handler(Exception)
    def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logging.getLogger("eve").error(
            "request.unhandled_exception",
            exc_info=exc,
            extra={"event": "request.unhandled_exception", "request_id": getattr(request.state, "request_id", None)},
        )
        return _error_response(
            request,
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
        )
