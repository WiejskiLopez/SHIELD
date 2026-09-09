"""Map Workflow persistence models to application query DTOs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from shell.execution_service.application.execution.workflow.dto.workflow_dto import WorkflowDto

if TYPE_CHECKING:
    from shell.execution_service.infrastructure.execution.workflow.persistence.sql.models import (
        WorkflowModel,
    )


def workflow_model_to_dto(model: WorkflowModel) -> WorkflowDto:
    return WorkflowDto(
        id=model.id,
        status=model.status,
        session_id=model.session_id,
        project_id=model.project_id,
        created_at=model.created_at,
        changed_at=model.changed_at,
        deleted_at=model.deleted_at,
    )
