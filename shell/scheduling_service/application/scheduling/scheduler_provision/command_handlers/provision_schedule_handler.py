from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from shell.platform.application.command_handlers.command_handler import CommandHandler
from shell.platform.application.context.causation_id import get_causation_id
from shell.platform.application.context.correlation_id import get_or_create_correlation_id
from shell.scheduling_service.application.scheduling.scheduler_provision.commands.provision_schedule_command import (
    ProvisionScheduleCommand,
)
from shell.scheduling_service.application.scheduling.scheduler_provision.integration_events.schedule_provision_failed_integration_event import (
    ScheduleProvisionFailedIntegrationEvent,
)
from shell.scheduling_service.application.scheduling.scheduler_provision.integration_events.schedule_provisioned_integration_event import (
    ScheduleProvisionedIntegrationEvent,
)

if TYPE_CHECKING:
    from shell.scheduling_service.application.scheduling.scheduler_provision.ports.schedule_result_writer import (
        ScheduleResultWriter,
    )


class ProvisionScheduleHandler(CommandHandler[ProvisionScheduleCommand]):
    """Uczestnik kroku — fakt rezultatu idzie do event_outbox, NIE na ulotny EventBus."""

    def __init__(self, result_writer: ScheduleResultWriter) -> None:
        self._result_writer = result_writer

    async def handle(self, command: ProvisionScheduleCommand) -> None:
        now = datetime.now(tz=UTC)
        if command.fail:
            self._result_writer.append(
                ScheduleProvisionFailedIntegrationEvent(
                    event_id=str(uuid.uuid4()),
                    correlation_id=get_or_create_correlation_id(),
                    causation_id=get_causation_id(),
                    occurred_at=now,
                    aggregate_id=command.scheduler_job_id,
                    schema_version=1,
                    scheduler_job_id=command.scheduler_job_id,
                    reason="schedule_unavailable",
                    attempt=command.attempt,
                )
            )
            return
        self._result_writer.append(
            ScheduleProvisionedIntegrationEvent(
                event_id=str(uuid.uuid4()),
                correlation_id=get_or_create_correlation_id(),
                causation_id=get_causation_id(),
                occurred_at=now,
                aggregate_id=command.scheduler_job_id,
                schema_version=1,
                scheduler_job_id=command.scheduler_job_id,
                attempt=command.attempt,
            )
        )
