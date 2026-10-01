"""HTTP middleware."""

import logging
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign request IDs and write safe request-completion events."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        request_id = str(uuid4())
        request.state.request_id = request_id
        started_at = time.perf_counter()
        try:
            response = await call_next(request)  # type: ignore[operator]
        except Exception as exc:
            # ServerErrorMiddleware sits outside application middleware.  Handling
            # here preserves the request ID and the standard API envelope even for
            # failures that escape FastAPI's exception middleware.
            logging.getLogger("eve").error(
                "request.unhandled_exception",
                exc_info=exc,
                extra={"event": "request.unhandled_exception", "request_id": request_id},
            )
            response = JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred",
                        "request_id": request_id,
                        "details": [],
                    }
                },
            )

        response.headers["X-Request-ID"] = request_id

        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logging.getLogger("eve").info(
            "request.completed",
            extra={
                "event": "request.completed",
                "request_id": request_id,
                "method": request.method,
                "route": request.scope.get("route").path if request.scope.get("route") else request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
