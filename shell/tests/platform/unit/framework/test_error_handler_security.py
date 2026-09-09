from __future__ import annotations

import json
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from shell.platform.domain.exceptions.domain_conflict_error import DomainConflictError
from shell.platform.framework.api.middleware.audit_log import AuditLogMiddleware
from shell.platform.framework.api.middleware.error_handler import (
    application_error_handler,
    domain_error_handler,
    unhandled_exception_handler,
)
from shell.project_service.domain.project.aggregates.project.exceptions.project_not_found import (
    ProjectNotFound,
)

if TYPE_CHECKING:
    from fastapi import Request


@pytest.mark.asyncio
async def test_unhandled_error_response_does_not_expose_exception_details() -> None:
    response = await unhandled_exception_handler(
        cast("Request", SimpleNamespace()),
        RuntimeError("database password=super-secret"),
    )

    body = json.loads(bytes(response.body))
    body_bytes = bytes(response.body)

    assert response.status_code == 500
    assert body["title"] == "Internal Server Error"
    assert body["detail"] == "An unexpected error occurred"
    assert "super-secret" not in body_bytes.decode()


@pytest.mark.asyncio
async def test_audit_log_records_principal_when_application_raises(caplog) -> None:
    async def failing_app(scope, receive, send) -> None:
        raise RuntimeError("failure")

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "headers": [],
        "state": {"principal": SimpleNamespace(subject_id="user-123")},
    }

    with caplog.at_level("INFO", logger="shell.api.audit"), pytest.raises(RuntimeError):
        await AuditLogMiddleware(failing_app)(scope, None, None)

    record = next(record for record in caplog.records if record.name == "shell.api.audit")
    assert record.principal == "user-123"
    assert record.status == 500


@pytest.mark.asyncio
async def test_not_found_domain_error_maps_to_http_404() -> None:
    response = await domain_error_handler(
        cast("Request", SimpleNamespace(url=SimpleNamespace(path="/projects/missing"))),
        ProjectNotFound("project-123"),
    )

    body = json.loads(bytes(response.body))
    assert response.status_code == 404
    assert body["title"] == "Not Found"
    assert body["detail"] == "Project not found: 'project-123'"


@pytest.mark.asyncio
async def test_domain_conflict_error_maps_to_http_409() -> None:
    response = await domain_error_handler(
        cast("Request", SimpleNamespace(url=SimpleNamespace(path="/projects/123"))),
        DomainConflictError("project already exists"),
    )

    body = json.loads(bytes(response.body))
    assert response.status_code == 409
    assert body["title"] == "Conflict"
    assert body["detail"] == "project already exists"


@pytest.mark.asyncio
async def test_domain_error_detail_is_sanitized() -> None:
    response = await domain_error_handler(
        cast("Request", SimpleNamespace(url=SimpleNamespace(path="/projects/123"))),
        DomainConflictError("connect to https://user:super-secret@example.com/db"),
    )

    body = json.loads(bytes(response.body))
    assert response.status_code == 409
    assert "super-secret" not in json.dumps(body)
    assert "***@" in body["detail"]


@pytest.mark.asyncio
async def test_application_not_found_error_maps_to_http_404() -> None:
    from shell.session_service.application.session.session.exceptions.session_not_found_error import (
        SessionNotFoundError,
    )

    response = await application_error_handler(
        cast("Request", SimpleNamespace(url=SimpleNamespace(path="/sessions/missing"))),
        SessionNotFoundError("Session 'session-123' not found"),
    )

    body = json.loads(bytes(response.body))
    assert response.status_code == 404
    assert body["title"] == "Not Found"
