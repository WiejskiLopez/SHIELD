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
from shell.execution_service.application.execution.task_execution.queries.list_task_executions_query import (
    ListTaskExecutionsQuery,
)
from shell.execution_service.framework.execution.task_execution.api.task_execution_mapper import (
    task_execution_dto_to_response,
)
from shell.execution_service.framework.execution.task_execution.api.task_execution_response import (
    TaskExecutionResponse as ApiTaskExecutionResponse,
)
from shell.platform.framework.api.models.page import Page

if TYPE_CHECKING:
    from shell.platform.application.bus.command_bus import CommandBus
    from shell.platform.application.bus.query_bus import QueryBus


class TaskExecutionController:
    __slots__ = ("_command_bus", "_query_bus")

    def __init__(self, command_bus: CommandBus, query_bus: QueryBus) -> None:
        self._command_bus = command_bus
        self._query_bus = query_bus

    async def start_task_execution(self, task_execution_id: str) -> None:
        await self._command_bus.dispatch(StartTaskExecutionCommand(task_execution_id))

    async def complete_task_execution(self, task_execution_id: str) -> None:
        await self._command_bus.dispatch(CompleteTaskExecutionCommand(task_execution_id))

    async def fail_task_execution(self, task_execution_id: str, reason: str | None = None) -> None:
        await self._command_bus.dispatch(FailTaskExecutionCommand(task_execution_id, reason))

    async def timeout_task_execution(self, task_execution_id: str) -> None:
        await self._command_bus.dispatch(TimeoutTaskExecutionCommand(task_execution_id))

    async def exhaust_task_execution(self, task_execution_id: str) -> None:
        await self._command_bus.dispatch(ExhaustTaskExecutionCommand(task_execution_id))

    async def rename_task_execution(self, task_execution_id: str, name: str) -> None:
        await self._command_bus.dispatch(RenameTaskExecutionCommand(task_execution_id, name))

    async def list_task_executions(
        self, page: int = 1, page_size: int = 100
    ) -> Page[ApiTaskExecutionResponse]:
        dtos, total = await self._query_bus.dispatch(
            ListTaskExecutionsQuery(page=page, page_size=page_size)
        )
        items = [task_execution_dto_to_response(dto) for dto in dtos]
        has_more = (page * page_size) < total
        return Page(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=has_more,
        )
