"""FastAPI application factory — BC Definition."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI

from shell.definition_service.framework.definition.graph_definition.api.router import (
    router as graph_definitions_router,
)
from shell.definition_service.framework.definition.node_definition.api.router import (
    router as node_definitions_router,
)
from shell.platform.framework.api.openapi import configure_openapi
from shell.platform.framework.api.setup import setup_api_common
from shell.platform.observability.framework.api.health import mount_readiness
from shell.platform.observability.framework.api.metrics import install_metrics
from shell.platform.observability.framework.api.providers import ObservabilityProviders

if TYPE_CHECKING:
    from shell.platform.framework.api.dependencies import ContainerProtocol


DEFINITION_OPENAPI_TAGS = (
    {"name": "GraphDefinitions", "description": "Graph definition operations."},
    {"name": "Health", "description": "Service health and readiness."},
)


def create_definition_app(core_container: ContainerProtocol, *, api_key: str = "") -> FastAPI:
    """Tworzy aplikację FastAPI dla BC Definition."""
    if not api_key:
        raise ValueError("create_definition_app requires a non-empty api_key (fail-closed)")
    app = FastAPI(title="shell — definition", version="0.1.0")
    app.state.core_container = core_container

    setup_api_common(
        app,
        api_key=api_key,
        public_exact={"/health", "/readiness", "/metrics", "/api"},
        public_prefix={"/docs", "/redoc", "/openapi.json"},
    )

    app.include_router(graph_definitions_router, prefix="/api/v1")
    app.include_router(node_definitions_router, prefix="/api/v1")
    configure_openapi(app, tags=DEFINITION_OPENAPI_TAGS)

    providers = ObservabilityProviders.from_container(core_container)
    mount_readiness(app, providers)
    install_metrics(app, providers, service="definition")
    return app
