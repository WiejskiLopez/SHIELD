"""Map TaskExecution domain aggregates to application query DTOs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from shell.execution_service.application.execution.task_execution.dto.task_execution_dto import (
    TaskExecutionDto,
)

if TYPE_CHECKING:
    from shell.execution_service.domain.execution.aggregates.task_execution.task_execution import (
        TaskExecution,
    )


def task_execution_to_dto(task_execution: TaskExecution) -> TaskExecutionDto:
    return TaskExecutionDto(
        id=task_execution.id.value,
        name=task_execution.name.value,
        created_at=task_execution.created_at.value,
        work_dir=task_execution.work_dir.value,
        workflow_id=task_execution.workflow_id.value,
        changed_at=task_execution.changed_at.value,
        deleted_at=task_execution.deleted_at.value,
    )
