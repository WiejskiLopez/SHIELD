"""Map SessionExecution persistence models to application query DTOs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from shell.execution_service.application.execution.session_execution.dto.session_execution_dto import (
    SessionExecutionDto,
)

if TYPE_CHECKING:
    from shell.execution_service.infrastructure.execution.session_execution.persistence.sql.models.session_execution import (
        SessionExecutionModel,
    )


def session_execution_model_to_dto(model: SessionExecutionModel) -> SessionExecutionDto:
    return SessionExecutionDto(
        id=model.id,
        user_execution_id=model.user_execution_id,
        session_id=model.session_id,
        created_at=model.created_at,
    )
