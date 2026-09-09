"""Error handler middleware — maps expected errors to HTTP responses.

BC-specific exception mappings should be added via per-BC middleware.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse

from shell.platform.application.context.correlation_id import get_correlation_id
from shell.platform.application.error_sanitization import (
    sanitize_message,
)
from shell.platform.application.exceptions import (
    ApplicationError,
)
from shell.platform.application.exceptions.command_validation_error import (
    CommandValidationError,
)
from shell.platform.domain.exceptions import (
    DomainError,
)
from shell.platform.domain.exceptions.concurrent_modification_error import (
    ConcurrentModificationError,
)
from shell.platform.domain.exceptions.domain_conflict_error import DomainConflictError
from shell.platform.framework.api.models.problem_detail import FieldError, ProblemDetail

if TYPE_CHECKING:
    from fastapi import HTTPException, Request
    from fastapi.exceptions import RequestValidationError

logger = logging.getLogger(__name__)


def _is_not_found_error(exc: BaseException) -> bool:
    """Map existing bounded-context not-found exceptions without coupling to a BC."""
    # Explicit protocol: platform NotFound errors declare their semantics by
    # inheriting DomainError/ApplicationError and carrying a NotFound suffix.
    if isinstance(exc, (DomainError, ApplicationError)):
        return type(exc).__name__.endswith(("NotFound", "NotFoundError"))
    # Fallback: suffix heuristic for legacy BC exceptions still inheriting
    # plain Exception until they are migrated to a platform base class.
    return type(exc).__name__.endswith(("NotFound", "NotFoundError"))


def _problem_response(
    request: Request,
    *,
    status_code: int,
    title: str,
    detail: str,
    errors: list[FieldError] | None = None,
) -> JSONResponse:
    request_url = getattr(request, "url", None)
    problem = ProblemDetail(
        title=title,
        status=status_code,
        detail=detail,
        instance=getattr(request_url, "path", None),
        errors=errors,
        correlation_id=get_correlation_id(),
        timestamp=ProblemDetail.now_iso(),
    )
    return JSONResponse(status_code=status_code, content=problem.model_dump(mode="json"))


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    if _is_not_found_error(exc):
        status_code = 404
        title = "Not Found"
    elif isinstance(exc, (ConcurrentModificationError, DomainConflictError)):
        status_code = 409
        title = "Conflict"
    else:
        status_code = 400
        title = "Domain Error"
    logger.error(
        "Domain error during request",
        exc_info=exc,
        extra={"correlation_id": get_correlation_id()},
    )
    return _problem_response(
        request,
        status_code=status_code,
        title=title,
        detail=sanitize_message(str(exc)),
    )


async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    if _is_not_found_error(exc):
        status_code = 404
        title = "Not Found"
    elif isinstance(exc, CommandValidationError):
        status_code = 422
        title = "Validation Error"
    else:
        status_code = 400
        title = "Application Error"
    logger.error(
        "Application error during request",
        exc_info=exc,
        extra={"correlation_id": get_correlation_id()},
    )
    return _problem_response(
        request,
        status_code=status_code,
        title=title,
        detail=sanitize_message(str(exc)),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = str(exc.detail)
    return _problem_response(
        request,
        status_code=exc.status_code,
        title=detail,
        detail=detail,
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        FieldError(
            field=".".join(str(x) for x in err.get("loc", [])),
            message=err.get("msg", ""),
            code=err.get("type", ""),
        )
        for err in exc.errors()
    ]
    return _problem_response(
        request,
        status_code=422,
        title="Validation Error",
        detail="Request validation failed",
        errors=errors,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled exception during request",
        exc_info=exc,
        extra={"correlation_id": get_correlation_id()},
    )
    return _problem_response(
        request,
        status_code=500,
        title="Internal Server Error",
        detail="An unexpected error occurred",
    )
