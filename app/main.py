"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.api.router import api_router
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.config import get_settings


def create_app() -> FastAPI:
    """Create the HTTP application without opening a database connection."""
    configure_logging(get_settings().log_level)

    app = FastAPI(
        title="EVE Diagnostic Booking API",
        version="0.1.0",
        description="Backend service for diagnostic test booking.",
    )
    app.add_middleware(RequestContextMiddleware)
    app.include_router(api_router)
    register_exception_handlers(app)
    def custom_openapi() -> dict[str, object]:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes)
        components = schema.setdefault("components", {}).setdefault("securitySchemes", {})
        components["BearerAuth"] = {"type": "http", "scheme": "bearer"}
        components["WebhookSecret"] = {"type": "apiKey", "in": "header", "name": "X-Webhook-Secret"}
        for path, methods in schema["paths"].items():
            for method, operation in methods.items():
                if path == "/payments/webhook/": operation["security"] = [{"WebhookSecret": []}]
                elif path.startswith(("/bookings/", "/payments/")) or (path.startswith(("/centres/", "/tests/")) and method in {"post", "patch", "delete"}) or path == "/auth/secret/": operation["security"] = [{"BearerAuth": []}]
        app.openapi_schema = schema
        return schema
    app.openapi = custom_openapi  # type: ignore[method-assign]
    return app


app = create_app()
