from __future__ import annotations

from typing import Protocol

from shell.project_service.application.project.project_provision.integration_events.workspace_provision_failed_integration_event import (
    WorkspaceProvisionFailedIntegrationEvent,
)
from shell.project_service.application.project.project_provision.integration_events.workspace_provisioned_integration_event import (
    WorkspaceProvisionedIntegrationEvent,
)
from shell.project_service.application.project.project_provision.integration_events.workspace_released_integration_event import (
    WorkspaceReleasedIntegrationEvent,
)

WorkspaceResultEvent = (
    WorkspaceProvisionedIntegrationEvent
    | WorkspaceProvisionFailedIntegrationEvent
    | WorkspaceReleasedIntegrationEvent
)
"""Wynik uczestnika pilota: dokładnie jeden z trzech faktów (cykl wynikowy kroku)."""


class ProvisionResultWriter(Protocol):
    """Port zapisu faktu uczestnika do event_outbox — ta sama transakcja co ack."""

    def append(self, event: WorkspaceResultEvent) -> None:
        """Dopisz wiersz event_outbox na bieżącej sesji UoW. Bez commit."""
