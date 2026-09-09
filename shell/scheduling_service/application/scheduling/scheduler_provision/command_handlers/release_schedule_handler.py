from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from shell.platform.application.command_handlers.command_handler import CommandHandler
from shell.platform.application.context.causation_id import get_causation_id
from shell.platform.application.context.correlation_id import get_or_create_correlation_id
from shell.scheduling_service.application.scheduling.scheduler_provision.commands.release_schedule_command import (
    ReleaseScheduleCommand,
)
from shell.scheduling_service.application.scheduling.scheduler_provision.integration_events.schedule_released_integration_event import (
    ScheduleReleasedIntegrationEvent,
)

if TYPE_CHECKING:
    from shell.scheduling_service.application.scheduling.scheduler_provision.ports.schedule_result_writer import (
        ScheduleResultWriter,
    )


class ReleaseScheduleHandler(CommandHandler[ReleaseScheduleCommand]):
    """Kompensacja sagi — fakt zwolnienia idzie do event_outbox (trwale)."""

    def __init__(self, result_writer: ScheduleResultWriter) -> None:
        self._result_writer = result_writer

    async def handle(self, command: ReleaseScheduleCommand) -> None:
        self._result_writer.append(
            ScheduleReleasedIntegrationEvent(
                event_id=str(uuid.uuid4()),
                correlation_id=get_or_create_correlation_id(),
                causation_id=get_causation_id(),
                occurred_at=datetime.now(tz=UTC),
                aggregate_id=command.scheduler_job_id,
                schema_version=1,
                scheduler_job_id=command.scheduler_job_id,
                attempt=command.attempt,
            )
        )
