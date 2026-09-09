"""Most startowy: komenda inicjalizująca BC -> start sagi w libce."""

from __future__ import annotations

from typing import TYPE_CHECKING

from saga_orchestration.application.start_saga_handler import StartSagaCommand
from saga_orchestration.domain.saga_key import SagaKey
from saga_orchestration.domain.saga_payload import SagaPayload

from shell.platform.application.command_handlers.command_handler import CommandHandler
from shell.platform.application.context.causation_id import get_causation_id
from shell.platform.application.context.correlation_id import get_or_create_correlation_id
from shell.project_service.application.project.project_provision.commands.start_project_provision_command import (
    StartProjectProvisionCommand,
)
from shell.project_service.process.project.project_provision.saga_definition import (
    PROJECT_PROVISION_STEPS_V2,
    SAGA_TYPE,
)

if TYPE_CHECKING:
    from saga_orchestration.application.start_saga_handler import StartSagaHandler


class StartProjectProvisionBridgeHandler(CommandHandler[StartProjectProvisionCommand]):
    """Inicjalizator sagi project_provision (rejestracja na CommandBus)."""

    def __init__(self, start_handler: StartSagaHandler) -> None:
        self._start_handler = start_handler

    async def handle(self, command: StartProjectProvisionCommand) -> None:
        await self._start_handler.handle(
            StartSagaCommand(
                key=SagaKey(saga_type=SAGA_TYPE, business_key=command.project_id),
                payload=SagaPayload({"project_id": command.project_id, "fail": command.fail}),
                steps=PROJECT_PROVISION_STEPS_V2,
                correlation_id=get_or_create_correlation_id(),
                causation_id=get_causation_id(),
            )
        )
