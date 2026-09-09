from __future__ import annotations

from typing import TYPE_CHECKING

from shell.execution_service.application.execution.node_execution.commands.complete_node_execution_command import (
    CompleteNodeExecutionCommand,
)
from shell.execution_service.application.execution.node_execution.services.node_execution_transition_service import (
    NodeExecutionTransitionService,
)
from shell.platform.application.command_handlers.command_handler import CommandHandler

if TYPE_CHECKING:
    from shell.platform.application.ports.persistence.unit_of_work import UnitOfWork
    from shell.platform.domain.ports.time import Clock


class CompleteNodeExecutionHandler(NodeExecutionTransitionService, CommandHandler[CompleteNodeExecutionCommand]):
    def __init__(self, unit_of_work: UnitOfWork, clock: Clock) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock
        super().__init__(unit_of_work, clock)

    async def handle(self, command: CompleteNodeExecutionCommand) -> None:
        await self.execute(command.node_execution_id, lambda node, now: node.complete(now))
