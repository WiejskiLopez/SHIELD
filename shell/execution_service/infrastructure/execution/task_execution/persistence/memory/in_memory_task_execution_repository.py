from __future__ import annotations

from typing import TYPE_CHECKING

from shell.execution_service.domain.execution.aggregates.task_execution.repositories.task_execution_repository import (
    TaskExecutionRepository,
)
from shell.execution_service.domain.execution.aggregates.task_execution.task_execution import (
    TaskExecution,
)
from shell.execution_service.domain.execution.aggregates.task_execution.value_objects.task_execution_id import (
    TaskExecutionId,
)
from shell.platform.infrastructure.persistence.in_memory_repository import (
    InMemoryRepository,
)

if TYPE_CHECKING:
    from shell.execution_service.domain.execution.aggregates.task_execution.value_objects.task_execution_name import (
        TaskExecutionName,
    )
    from shell.execution_service.domain.execution.aggregates.workflow.value_objects.workflow_id import (
        WorkflowId,
    )


class InMemoryTaskExecutionRepository(
    InMemoryRepository[TaskExecution, TaskExecutionId], TaskExecutionRepository
):
    async def get_by_id(self, id: TaskExecutionId) -> TaskExecution | None:
        task_execution = self._store.get(id.value)
        if task_execution is None or task_execution.deleted_at.value is not None:
            return None
        return task_execution

    async def get_by_name(self, name: TaskExecutionName) -> TaskExecution | None:
        matches = [
            task_execution
            for task_execution in self._visible_values()
            if (
                task_execution.deleted_at.value is None
                and (
                task_execution.name.value
                if hasattr(task_execution.name, "value")
                else str(task_execution.name)
                )
            )
            == (name.value if hasattr(name, "value") else str(name))
        ]
        if not matches:
            return None
        return min(matches, key=lambda task_execution: task_execution.id.value)

    async def get_current_by_id(self, id: TaskExecutionId) -> TaskExecution | None:
        return await self.get_by_id(id)

    async def get_current_by_name(self, name: TaskExecutionName) -> TaskExecution | None:
        return await self.get_by_name(name)

    async def get_by_workflow_id(self, workflow_id: WorkflowId) -> list[TaskExecution]:
        return [
            te
            for te in self._visible_values()
            if te.deleted_at.value is None and te.workflow_id == workflow_id
        ]

    async def list_current(self) -> list[TaskExecution]:
        return self._visible_values()
