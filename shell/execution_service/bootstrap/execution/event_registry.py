"""Execution bounded context event registry."""

from __future__ import annotations

from shell.execution_service.bootstrap.execution.contract_catalog import EXECUTION_CONTRACT_CATALOG
from shell.platform.infrastructure.serialization.registries.event_registry import (
    build_bounded_context_event_registry,
)


def build_execution_event_registry() -> dict[str, type]:
    """Build the event registry owned by the Execution bounded context."""
    return build_bounded_context_event_registry(
        package="shell.execution_service.application.execution",
        catalog=EXECUTION_CONTRACT_CATALOG,
    )
