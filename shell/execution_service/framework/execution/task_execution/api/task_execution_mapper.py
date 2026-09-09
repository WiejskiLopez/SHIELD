"""Map TaskExecution application DTOs to HTTP response models."""

from __future__ import annotations

from shell.execution_service.application.execution.task_execution.dto.task_execution_dto import (
    TaskExecutionDto,
)
from shell.execution_service.framework.execution.task_execution.api.task_execution_response import (
    TaskExecutionResponse,
)


def task_execution_dto_to_response(dto: TaskExecutionDto) -> TaskExecutionResponse:
    return TaskExecutionResponse(
        id=dto.id,
        name=dto.name,
        work_dir=dto.work_dir,
        workflow_id=dto.workflow_id,
        created_at=dto.created_at,
        changed_at=dto.changed_at,
        deleted_at=dto.deleted_at,
    )