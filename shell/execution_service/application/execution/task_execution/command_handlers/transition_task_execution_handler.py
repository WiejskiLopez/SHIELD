from __future__ import annotations

from typing import TYPE_CHECKING

from shell.execution_service.application.execution.task_execution.commands.complete_task_execution_command import (
    CompleteTaskExecutionCommand,
)
from shell.execution_service.application.execution.task_execution.commands.exhaust_task_execution_command import (
    ExhaustTaskExecutionCommand,
)
from shell.execution_service.application.execution.task_execution.commands.fail_task_execution_command import (
    FailTaskExecutionCommand,
)
from shell.execution_service.application.execution.task_execution.commands.rename_task_execution_command import (
    RenameTaskExecutionCommand,
)
from shell.execution_service.application.execution.task_execution.commands.start_task_execution_command import (
    StartTaskExecutionCommand,
)
from shell.execution_service.application.execution.task_execution.commands.timeout_task_execution_command import (
    TimeoutTaskExecutionCommand,
)
from shell.execution_service.application.execution.task_execution.exceptions.task_execution_not_found_error import (
    TaskExecutionNotFoundError,
)
from shell.execution_service.domain.execution.aggregates.task_execution.repositories.task_execution_repository import (
    TaskExecutionRepository,
)
from shell.execution_service.domain.execution.aggregates.task_execution.value_objects.task_execution_id import (
    TaskExecutionId,
)
from shell.execution_service.domain.execution.aggregates.task_execution.value_objects.task_name import (
    TaskName,
)
from shell.platform.application.command_handlers.command_handler import CommandHandler
from shell.platform.domain.value_objects.occurred_at import OccurredAt
from shell.platform.domain.value_objects.reason import Reason

if TYPE_CHECKING:
    from shell.platform.application.ports.persistence.unit_of_work import UnitOfWork
    from shell.platform.domain.ports.time import Clock


TaskExecutionCommand = (
    CompleteTaskExecutionCommand
    | ExhaustTaskExecutionCommand
    | FailTaskExecutionCommand
    | RenameTaskExecutionCommand
    | StartTaskExecutionCommand
    | TimeoutTaskExecutionCommand
)


class TransitionTaskExecutionHandler(CommandHandler[TaskExecutionCommand]):
    def __init__(self, unit_of_work: UnitOfWork, clock: Clock) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    async def handle(self, command: TaskExecutionCommand) -> None:
        async with self._unit_of_work as unit_of_work:
            task = await unit_of_work.repository(TaskExecutionRepository).get_by_id(
                TaskExecutionId(command.task_execution_id)
            )
            if task is None:
                raise TaskExecutionNotFoundError(
                    f"TaskExecution '{command.task_execution_id}' not found"
                )
            now = OccurredAt.from_datetime(self._clock.now())
            if isinstance(command, StartTaskExecutionCommand):
                task.start(now)
            elif isinstance(command, CompleteTaskExecutionCommand):
                task.complete(now)
            elif isinstance(command, FailTaskExecutionCommand):
                task.fail(Reason(command.reason or "task failed"), now)
            elif isinstance(command, TimeoutTaskExecutionCommand):
                task.timeout(now)
            elif isinstance(command, ExhaustTaskExecutionCommand):
                task.exhaust(now)
            elif isinstance(command, RenameTaskExecutionCommand):
                task.rename(TaskName(command.name), now)
            await unit_of_work.save(TaskExecutionRepository, task)
            await unit_of_work.commit()
