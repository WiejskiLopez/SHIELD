"""Most startowy: komenda inicjalizująca BC -> start sagi w libce."""

from __future__ import annotations

from typing import TYPE_CHECKING

from saga_orchestration.application.start_saga_handler import StartSagaCommand
from saga_orchestration.domain.saga_key import SagaKey
from saga_orchestration.domain.saga_payload import SagaPayload

from shell.platform.application.command_handlers.command_handler import CommandHandler
from shell.platform.application.context.causation_id import get_causation_id
from shell.platform.application.context.correlation_id import get_or_create_correlation_id
from shell.scheduling_service.application.scheduling.scheduler_provision.commands.start_scheduler_provision_command import (
    StartSchedulerProvisionCommand,
)
from shell.scheduling_service.process.scheduling.scheduler_provision.saga_definition import (
    SAGA_TYPE,
    SCHEDULER_PROVISION_STEPS,
)

if TYPE_CHECKING:
    from saga_orchestration.application.start_saga_handler import StartSagaHandler


class StartSchedulerProvisionBridgeHandler(CommandHandler[StartSchedulerProvisionCommand]):
    """Inicjalizator sagi scheduler_provision (rejestracja na CommandBus)."""

    def __init__(self, start_handler: StartSagaHandler) -> None:
        self._start_handler = start_handler

    async def handle(self, command: StartSchedulerProvisionCommand) -> None:
        await self._start_handler.handle(
            StartSagaCommand(
                key=SagaKey(saga_type=SAGA_TYPE, business_key=command.scheduler_job_id),
                payload=SagaPayload(
                    {"scheduler_job_id": command.scheduler_job_id, "fail": command.fail}
                ),
                steps=SCHEDULER_PROVISION_STEPS,
                correlation_id=get_or_create_correlation_id(),
                causation_id=get_causation_id(),
            )
        )
