"""Uniform safe failures and request identifiers for the public API."""

import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from backend.app.contracts import ErrorResponse, FieldProblem
from backend.app.errors import ApiProblem
from backend.app.persistence.analysis import NoAcceptedRelease, ReleaseNotFound
from backend.app.security import SECURITY_HEADERS

logger = logging.getLogger("winddesk.api")


def _error(request: Request, status: int, code: str, message: str, errors=()) -> JSONResponse:
    request.state.error_code = code
    request_id = getattr(request.state, "request_id", None) or str(uuid4())
    body = ErrorResponse(code=code, message=message, request_id=request_id, errors=list(errors))
    return JSONResponse(
        status_code=status,
        content=body.model_dump(mode="json"),
        headers={
            "X-Request-ID": request_id,
            "Cache-Control": "no-store",
            **SECURITY_HEADERS,
        },
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiProblem)
    async def api_problem(request: Request, exc: ApiProblem):
        return _error(request, exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def invalid_filters(request: Request, exc: RequestValidationError):
        errors = [
            FieldProblem(
                field=".".join(str(part) for part in item["loc"]),
                code=item["type"],
                message=item["msg"],
            )
            for item in exc.errors()
        ]
        return _error(request, 422, "INVALID_FILTERS", "Check the supplied query filters.", errors)

    @app.exception_handler(ReleaseNotFound)
    async def unknown_release(request: Request, exc: ReleaseNotFound):
        return _error(
            request, 404, "RELEASE_NOT_FOUND", "The accepted dataset release was not found."
        )

    @app.exception_handler(NoAcceptedRelease)
    async def no_release(request: Request, exc: NoAcceptedRelease):
        return _error(request, 503, "NO_ACCEPTED_DATASET", "No accepted dataset release is active.")

    @app.exception_handler(SQLAlchemyError)
    async def unavailable(request: Request, exc: SQLAlchemyError):
        missing_schema = getattr(getattr(exc, "orig", None), "sqlstate", None) == "42P01"
        code = "SCHEMA_NOT_INITIALIZED" if missing_schema else "DATABASE_UNAVAILABLE"
        logger.warning(
            "Stored dataset read failed: code=%s request_id=%s", code, request.state.request_id
        )
        return _error(request, 503, code, "Stored source data is unavailable. Try again later.")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        code, message = {
            404: ("NOT_FOUND", "The requested resource was not found."),
            405: ("METHOD_NOT_ALLOWED", "This resource does not support that HTTP method."),
        }.get(exc.status_code, ("HTTP_ERROR", "The request could not be completed."))
        response = _error(request, exc.status_code, code, message)
        response.headers.update(exc.headers or {})
        return response

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        logger.error(
            "Unexpected API failure: type=%s request_id=%s",
            type(exc).__name__,
            request.state.request_id,
        )
        return _error(request, 500, "INTERNAL_ERROR", "The request could not be completed.")
