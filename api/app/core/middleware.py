"""Request-id and access-log middleware."""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.errors import unhandled_exception_handler
from app.core.logging import request_id_ctx

access_logger = logging.getLogger("app.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception as exc:
                # Handled here (not by Starlette's outer handler) so the response still
                # passes through CORS and carries the request id.
                response = await unhandled_exception_handler(request, exc)
            response.headers["X-Request-ID"] = request_id
            access_logger.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    "actor_id": getattr(request.state, "actor_id", None),
                },
            )
            return response
        finally:
            request_id_ctx.reset(token)
