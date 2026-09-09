"""User bounded context event registry."""

from __future__ import annotations

from shell.platform.infrastructure.serialization.registries.event_registry import (
    build_bounded_context_event_registry,
)
from shell.user_service.bootstrap.user.contract_catalog import USER_CONTRACT_CATALOG


def build_user_event_registry() -> dict[str, type]:
    """Build the event registry owned by the User bounded context."""
    return build_bounded_context_event_registry(
        package="shell.user_service.application.user",
        catalog=USER_CONTRACT_CATALOG,
    )
