"""Map TaskExecution persistence models to application query DTOs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from shell.execution_service.application.execution.task_execution.dto.task_execution_dto import (
    TaskExecutionDto,
)

if TYPE_CHECKING:
    from shell.execution_service.infrastructure.execution.task_execution.persistence.sql.models import (
        TaskExecutionModel,
    )


def task_execution_model_to_dto(model: TaskExecutionModel) -> TaskExecutionDto:
    return TaskExecutionDto(
        id=model.id,
        name=model.name,
        created_at=model.created_at,
        work_dir=model.work_dir,
        workflow_id=model.workflow_id,
        changed_at=model.changed_at,
        deleted_at=model.deleted_at,
    )