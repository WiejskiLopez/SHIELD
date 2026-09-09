"""Project bounded context event registry."""

from __future__ import annotations

from shell.platform.infrastructure.serialization.registries.event_registry import (
    build_bounded_context_event_registry,
)
from shell.project_service.bootstrap.project.contract_catalog import PROJECT_CONTRACT_CATALOG


def build_project_event_registry() -> dict[str, type]:
    """Build the event registry owned by the Project bounded context."""
    return build_bounded_context_event_registry(
        package="shell.project_service.application.project",
        catalog=PROJECT_CONTRACT_CATALOG,
    )
