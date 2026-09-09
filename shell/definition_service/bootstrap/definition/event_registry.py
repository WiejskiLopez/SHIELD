"""Definition bounded context event registry."""

from __future__ import annotations

from shell.definition_service.bootstrap.definition.contract_catalog import (
    DEFINITION_CONTRACT_CATALOG,
)
from shell.platform.infrastructure.serialization.registries.event_registry import (
    build_bounded_context_event_registry,
)


def build_definition_event_registry() -> dict[str, type]:
    """Build the event registry owned by the Definition bounded context."""
    return build_bounded_context_event_registry(
        package="shell.definition_service.application.definition",
        catalog=DEFINITION_CONTRACT_CATALOG,
    )
