"""Session bounded context event registry.

Owns the Session BC integration events and explicitly lists cross-BC events that
the Session BC consumes (here: the User BC login event that triggers session
opening). Only these two sources are allowed — no arbitrary cross-BC discovery.
"""

from __future__ import annotations

from shell.platform.infrastructure.serialization.registries.event_registry import (
    build_bounded_context_event_registry,
)
from shell.session_service.application.session.session.integration_events.auth_session_created_integration_event import (
    AuthSessionCreatedIntegrationEvent,
)
from shell.session_service.bootstrap.session.contract_catalog import SESSION_CONTRACT_CATALOG


def build_session_event_registry() -> dict[str, type]:
    """Build the event registry owned by the Session bounded context.

    Includes the Session BC's own integration events plus the explicitly consumed
    local representation of the public User BC login contract.
    """
    consumed: tuple[type, ...] = (AuthSessionCreatedIntegrationEvent,)
    return build_bounded_context_event_registry(
        package="shell.session_service.application.session",
        catalog=SESSION_CONTRACT_CATALOG,
        consumed=consumed,
    )
