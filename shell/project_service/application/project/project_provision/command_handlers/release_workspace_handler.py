from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from shell.platform.application.command_handlers.command_handler import CommandHandler
from shell.platform.application.context.causation_id import get_causation_id
from shell.platform.application.context.correlation_id import get_or_create_correlation_id
from shell.project_service.application.project.project_provision.commands.release_workspace_command import (
    ReleaseWorkspaceCommand,
)
from shell.project_service.application.project.project_provision.integration_events.workspace_released_integration_event import (
    WorkspaceReleasedIntegrationEvent,
)

if TYPE_CHECKING:
    from shell.project_service.application.project.project_provision.ports.provision_result_writer import (
        ProvisionResultWriter,
    )


class ReleaseWorkspaceHandler(CommandHandler[ReleaseWorkspaceCommand]):
    """Kompensacja pilota — fakt zwolnienia idzie do event_outbox (trwale)."""

    def __init__(self, result_writer: ProvisionResultWriter) -> None:
        self._result_writer = result_writer

    async def handle(self, command: ReleaseWorkspaceCommand) -> None:
        self._result_writer.append(
            WorkspaceReleasedIntegrationEvent(
                event_id=str(uuid.uuid4()),
                correlation_id=get_or_create_correlation_id(),
                causation_id=get_causation_id(),
                occurred_at=datetime.now(tz=UTC),
                aggregate_id=command.project_id,
                schema_version=1,
                project_id=command.project_id,
                attempt=command.attempt,
            )
        )
