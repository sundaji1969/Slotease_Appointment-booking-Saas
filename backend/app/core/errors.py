"""Every error leaves the API as {"error": CODE, "message": text}."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("slotease")


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class NotFound(AppError):
    def __init__(self, message: str = "Not found", code: str = "NOT_FOUND") -> None:
        super().__init__(404, code, message)


class Conflict(AppError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(409, code, message)


class Unprocessable(AppError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(422, code, message)


class Unauthorized(AppError):
    def __init__(self, message: str = "Not authenticated", code: str = "UNAUTHORIZED") -> None:
        super().__init__(401, code, message)


SLOT_TAKEN_MESSAGE = "This slot was just booked. Please pick another time."


def error_body(code: str, message: str) -> dict[str, str]:
    return {"error": code, "message": message}


_HTTP_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
}


def _format_validation(exc: RequestValidationError) -> str:
    errs = exc.errors()
    if not errs:
        return "Invalid request"
    first = errs[0]
    loc = ".".join(str(p) for p in first.get("loc", []) if p not in ("body", "query", "path"))
    msg = str(first.get("msg", "Invalid value")).removeprefix("Value error, ")
    return f"{loc}: {msg}" if loc else msg


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content=error_body("VALIDATION_ERROR", _format_validation(exc)))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(status_code=exc.status_code, content=error_body(code, str(exc.detail)))

    @app.exception_handler(RateLimitExceeded)
    async def _rate(_: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content=error_body("RATE_LIMITED", "Too many requests. Please try again shortly."),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error", exc_info=exc)
        return JSONResponse(status_code=500, content=error_body("INTERNAL_ERROR", "Something went wrong"))
