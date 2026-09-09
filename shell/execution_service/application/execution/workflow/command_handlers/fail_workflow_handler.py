from __future__ import annotations

from typing import TYPE_CHECKING

from shell.execution_service.application.execution.workflow.commands.fail_workflow_command import (
    FailWorkflowCommand,
)
from shell.execution_service.application.execution.workflow.exceptions.workflow_not_found_error import (
    WorkflowNotFoundError,
)
from shell.execution_service.domain.execution.aggregates.workflow.repositories.workflow_repository import (
    WorkflowRepository,
)
from shell.execution_service.domain.execution.aggregates.workflow.value_objects.workflow_id import (
    WorkflowId,
)
from shell.platform.application.command_handlers.command_handler import CommandHandler
from shell.platform.domain.value_objects.occurred_at import OccurredAt

if TYPE_CHECKING:
    from shell.platform.application.ports.persistence.unit_of_work import UnitOfWork
    from shell.platform.domain.ports.time import Clock


class FailWorkflowHandler(CommandHandler[FailWorkflowCommand]):
    def __init__(self, unit_of_work: UnitOfWork, clock: Clock) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    async def handle(self, command: FailWorkflowCommand) -> None:
        async with self._unit_of_work as unit_of_work:
            workflow = await unit_of_work.repository(WorkflowRepository).get_by_id(WorkflowId(command.workflow_id))
            if workflow is None:
                raise WorkflowNotFoundError(f"Workflow '{command.workflow_id}' not found")
            workflow.fail(now=OccurredAt.from_datetime(self._clock.now()))
            await unit_of_work.save(WorkflowRepository, workflow)
            await unit_of_work.commit()
