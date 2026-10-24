"""
app/errors.py — ApiError exception and FastAPI exception handlers.

Error shape (architecture.md §8):
  { "detail": str, "code": str, "field": str | null }
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError


class ApiError(Exception):
    """Raised anywhere in services/routers; caught by the handler below."""

    def __init__(self, status_code: int, code: str, detail: str = "", field: str | None = None):
        self.status_code = status_code
        self.code = code
        self.detail = detail or code
        self.field = field
        super().__init__(detail)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code, "field": exc.field},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        field = None
        detail = "Validation error"
        if errors:
            loc = errors[0].get("loc", [])
            field = str(loc[-1]) if loc else None
            detail = errors[0].get("msg", "Validation error")
        return JSONResponse(
            status_code=422,
            content={"detail": detail, "code": "VALIDATION_ERROR", "field": field},
        )

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"detail": "Not found", "code": "NOT_FOUND", "field": None},
        )
