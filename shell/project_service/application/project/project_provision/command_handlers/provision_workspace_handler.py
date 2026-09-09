from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from shell.platform.application.command_handlers.command_handler import CommandHandler
from shell.platform.application.context.causation_id import get_causation_id
from shell.platform.application.context.correlation_id import get_or_create_correlation_id
from shell.project_service.application.project.project_provision.commands.provision_workspace_command import (
    ProvisionWorkspaceCommand,
)
from shell.project_service.application.project.project_provision.integration_events.workspace_provision_failed_integration_event import (
    WorkspaceProvisionFailedIntegrationEvent,
)
from shell.project_service.application.project.project_provision.integration_events.workspace_provisioned_integration_event import (
    WorkspaceProvisionedIntegrationEvent,
)

if TYPE_CHECKING:
    from shell.project_service.application.project.project_provision.ports.provision_result_writer import (
        ProvisionResultWriter,
    )


class ProvisionWorkspaceHandler(CommandHandler[ProvisionWorkspaceCommand]):
    """Uczestnik kroku — w pilocie stubuje efekt zewnętrznego serwisu.

    Fakt rezultatu idzie do event_outbox (ta sama transakcja co ack inbox),
    NIE na ulotny EventBus. W produkcji efekt realizuje właściwy agregat
    uczestnika; ścieżka doręczenia faktu zostaje ta sama.
    """

    def __init__(self, result_writer: ProvisionResultWriter) -> None:
        self._result_writer = result_writer

    async def handle(self, command: ProvisionWorkspaceCommand) -> None:
        now = datetime.now(tz=UTC)
        if command.fail:
            self._result_writer.append(
                WorkspaceProvisionFailedIntegrationEvent(
                    event_id=str(uuid.uuid4()),
                    correlation_id=get_or_create_correlation_id(),
                    causation_id=get_causation_id(),
                    occurred_at=now,
                    aggregate_id=command.project_id,
                    schema_version=1,
                    project_id=command.project_id,
                    reason="workspace_unavailable",
                    attempt=command.attempt,
                )
            )
            return
        self._result_writer.append(
            WorkspaceProvisionedIntegrationEvent(
                event_id=str(uuid.uuid4()),
                correlation_id=get_or_create_correlation_id(),
                causation_id=get_causation_id(),
                occurred_at=now,
                aggregate_id=command.project_id,
                schema_version=1,
                project_id=command.project_id,
                attempt=command.attempt,
            )
        )
