"""FastAPI application factory."""

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers import auth, businesses, health, meta, staff, stats
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(title="CrediSure Ops Console API", version=settings.app_version)
    # Middleware added last is outermost: CORS wraps the request-id layer so that
    # even error responses carry CORS headers.
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    register_exception_handlers(app)
    app.include_router(health.router)
    v1 = APIRouter(prefix="/api/v1")
    v1.include_router(auth.router)
    v1.include_router(stats.router)
    v1.include_router(businesses.router)
    v1.include_router(meta.router)
    v1.include_router(staff.router)
    app.include_router(v1)
    return app


app = create_app()
