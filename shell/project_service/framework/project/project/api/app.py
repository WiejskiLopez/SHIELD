"""FastAPI application factory — Project aggregate."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI

from shell.platform.framework.api.openapi import configure_openapi
from shell.platform.framework.api.setup import setup_api_common
from shell.platform.observability.framework.api.health import mount_readiness
from shell.platform.observability.framework.api.metrics import install_metrics
from shell.platform.observability.framework.api.providers import ObservabilityProviders
from shell.project_service.framework.project.project.api.router import router

if TYPE_CHECKING:
    from shell.platform.framework.api.dependencies import ContainerProtocol


PROJECT_OPENAPI_TAGS = (
    {"name": "Projects", "description": "Project management operations."},
    {"name": "Health", "description": "Service health and readiness."},
)


def create_project_app(container: ContainerProtocol, *, api_key: str = "") -> FastAPI:
    """Tworzy aplikację FastAPI dla agregatu Project.

    Może być używana jako samodzielny mikroserwis lub jako część BC Project.
    """
    if not api_key:
        raise ValueError("create_project_app requires a non-empty api_key (fail-closed)")
    app = FastAPI(title="shell — project:project", version="0.1.0")
    app.state.core_container = container
    setup_api_common(
        app,
        api_key=api_key,
        public_exact={"/health", "/readiness", "/metrics", "/api"},
        public_prefix={"/docs", "/redoc", "/openapi.json"},
    )

    app.include_router(router, prefix="/api/v1")
    configure_openapi(app, tags=PROJECT_OPENAPI_TAGS)

    providers = ObservabilityProviders.from_container(container)
    mount_readiness(app, providers)
    install_metrics(app, providers, service="project")
    return app
