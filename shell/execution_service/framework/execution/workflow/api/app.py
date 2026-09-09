"""FastAPI application factory — Workflow aggregate."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI

from shell.execution_service.framework.execution.workflow.api.router import router
from shell.platform.domain.exceptions import DomainError
from shell.platform.framework.api.middleware.api_key import AuthMiddleware
from shell.platform.framework.api.middleware.correlation_id import CorrelationIdMiddleware
from shell.platform.framework.api.middleware.error_handler import domain_error_handler

if TYPE_CHECKING:
    from shell.platform.framework.api.dependencies import ContainerProtocol


def create_workflow_app(container: ContainerProtocol, *, api_key: str = "") -> FastAPI:
    """Tworzy aplikację FastAPI dla agregatu Workflow.

    Może być używana jako samodzielny mikroserwis lub jako część BC Execution.
    """
    if not api_key:
        raise ValueError("create_workflow_app requires a non-empty api_key (fail-closed)")
    app = FastAPI(title="shell — execution:workflow", version="0.1.0")
    app.state.core_container = container

    app.add_middleware(
        AuthMiddleware,
        api_key=api_key,
        public_exact={"/health", "/readiness", "/metrics", "/api"},
        public_prefix={"/docs", "/redoc", "/openapi.json"},
    )
    app.add_middleware(CorrelationIdMiddleware)
    app.add_exception_handler(DomainError, domain_error_handler)  # type: ignore[arg-type]

    app.include_router(router)

    @app.get("/health", tags=["Health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
