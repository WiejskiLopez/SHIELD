"""Scheduling bounded context event registry."""

from __future__ import annotations

from shell.platform.infrastructure.serialization.registries.event_registry import (
    build_bounded_context_event_registry,
)
from shell.scheduling_service.bootstrap.scheduling.contract_catalog import (
    SCHEDULING_CONTRACT_CATALOG,
)


def build_scheduling_event_registry() -> dict[str, type]:
    """Build the event registry owned by the Scheduling bounded context."""
    return build_bounded_context_event_registry(
        package="shell.scheduling_service.application.scheduling",
        catalog=SCHEDULING_CONTRACT_CATALOG,
    )
