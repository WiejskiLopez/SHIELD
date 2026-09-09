from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI

from shell.platform.framework.api.openapi import configure_openapi
from shell.platform.framework.api.setup import setup_api_common
from shell.platform.observability.framework.api.health import mount_readiness
from shell.platform.observability.framework.api.metrics import install_metrics
from shell.platform.observability.framework.api.providers import ObservabilityProviders
from shell.scheduling_service.framework.scheduling.scheduler_definition.api.router import (
    router as scheduler_definition_router,
)
from shell.scheduling_service.framework.scheduling.scheduler_execution.api.router import (
    router as scheduler_execution_router,
)
from shell.scheduling_service.framework.scheduling.scheduler_job.api.router import (
    router as scheduler_job_router,
)

if TYPE_CHECKING:
    from shell.platform.framework.api.dependencies import ContainerProtocol

SCHEDULING_OPENAPI_TAGS = (
    {"name": "SchedulerDefinitions", "description": "Scheduler definition operations."},
    {"name": "SchedulerJobs", "description": "Scheduler job operations."},
    {"name": "SchedulerExecutions", "description": "Scheduler execution operations."},
    {"name": "Health", "description": "Service health and readiness."},
)


def create_scheduling_app(container: ContainerProtocol, *, api_key: str = "") -> FastAPI:
    if container is None:
        raise ValueError("create_scheduling_app requires a configured container")
    if not api_key:
        raise ValueError("create_scheduling_app requires a non-empty api_key (fail-closed)")
    app = FastAPI(title="shell - scheduling", version="0.1.0")
    app.state.core_container = container
    setup_api_common(
        app,
        api_key=api_key,
        public_exact={"/health", "/readiness", "/metrics", "/api"},
        public_prefix={"/docs", "/redoc", "/openapi.json"},
    )
    app.include_router(scheduler_definition_router, prefix="/api/v1")
    app.include_router(scheduler_execution_router, prefix="/api/v1")
    app.include_router(scheduler_job_router, prefix="/api/v1")
    configure_openapi(app, tags=SCHEDULING_OPENAPI_TAGS)

    providers = ObservabilityProviders.from_container(container)
    mount_readiness(app, providers)
    install_metrics(app, providers, service="scheduling")

    return app
