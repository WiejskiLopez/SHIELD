from __future__ import annotations

from typing import TYPE_CHECKING

from shell.execution_service.application.execution.task_execution.mappers.task_execution_to_dto import (
    task_execution_to_dto,
)
from shell.execution_service.domain.execution.aggregates.task_execution.value_objects.task_execution_id import (
    TaskExecutionId,
)
from shell.execution_service.domain.execution.aggregates.task_execution.value_objects.task_execution_name import (
    TaskExecutionName,
)
from shell.execution_service.infrastructure.execution.task_execution.persistence.memory.in_memory_task_execution_repository import (
    InMemoryTaskExecutionRepository,
)

if TYPE_CHECKING:
    from shell.execution_service.application.execution.task_execution.dto.task_execution_dto import (
        TaskExecutionDto,
    )
    from shell.execution_service.infrastructure.execution.persistence.memory.unit_of_work import (
        InMemoryExecutionUnitOfWork,
    )


class InMemoryTaskExecutionQueryService:
    def __init__(self, unit_of_work: InMemoryExecutionUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def get_by_id(self, task_execution_id: str) -> TaskExecutionDto | None:
        task_execution = await self._unit_of_work.repository(
            InMemoryTaskExecutionRepository
        ).get_current_by_id(TaskExecutionId(task_execution_id))
        if not task_execution:
            return None
        return task_execution_to_dto(task_execution)

    async def get_task_execution_by_name(self, name: str) -> TaskExecutionDto | None:
        task_execution = await self._unit_of_work.repository(
            InMemoryTaskExecutionRepository
        ).get_by_name(TaskExecutionName(name))
        if not task_execution:
            return None
        return task_execution_to_dto(task_execution)

    async def get_current_task(self, name: str) -> TaskExecutionDto | None:
        return await self.get_task_execution_by_name(name)

    async def list_all(
        self, *, page: int = 1, page_size: int = 100
    ) -> tuple[list[TaskExecutionDto], int]:
        repository = self._unit_of_work.repository(InMemoryTaskExecutionRepository)
        task_executions = sorted(
            await repository.list_current(),
            key=lambda task_execution: task_execution.created_at.value,
            reverse=True,
        )
        total = len(task_executions)
        offset = (page - 1) * page_size
        page_items = task_executions[offset : offset + page_size]
        return [task_execution_to_dto(task_execution) for task_execution in page_items], total
