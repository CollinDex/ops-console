"""AppError hierarchy and the error-envelope handlers (design section 6.5)."""

import logging
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_ctx

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        self.details = details


class InvalidCredentials(AppError):
    status_code = 401
    code = "invalid_credentials"

    def __init__(self, message: str = "Email or password is incorrect.") -> None:
        super().__init__(message)


class NotAuthenticated(AppError):
    status_code = 401
    code = "not_authenticated"

    def __init__(self, message: str = "Authentication is required.") -> None:
        super().__init__(message)


class TokenExpired(AppError):
    status_code = 401
    code = "token_expired"

    def __init__(self, message: str = "Your session has expired. Please sign in again.") -> None:
        super().__init__(message)


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"


class NotFound(AppError):
    status_code = 404
    code = "not_found"

    def __init__(self, message: str = "Resource not found.") -> None:
        super().__init__(message)


class ValidationFailed(AppError):
    status_code = 422
    code = "validation_error"


class InternalError(AppError):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str = "Something went wrong on our side.") -> None:
        super().__init__(message)


def error_body(
    code: str, message: str, details: Any = None, request_id: str | None = None
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": request_id or request_id_ctx.get(),
    }
    if details is not None:
        error["details"] = details
    return {"error": error}


def error_response(status_code: int, code: str, message: str, details: Any = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=error_body(code, message, details))


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    err = cast(AppError, exc)
    return error_response(err.status_code, err.code, err.message, err.details)


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    verr = cast(RequestValidationError, exc)
    details = [
        {"field": ".".join(str(part) for part in err["loc"]), "message": err["msg"]}
        for err in verr.errors()
    ]
    return error_response(422, "validation_error", "The request is invalid.", details)


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    herr = cast(StarletteHTTPException, exc)
    if herr.status_code == 404:
        return error_response(404, "not_found", "Resource not found.")
    if herr.status_code == 405:
        return error_response(405, "method_not_allowed", "Method not allowed.")
    return error_response(herr.status_code, "http_error", str(herr.detail))


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled exception", exc_info=(type(exc), exc, exc.__traceback__))
    return error_response(500, "internal_error", "Something went wrong on our side.")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
