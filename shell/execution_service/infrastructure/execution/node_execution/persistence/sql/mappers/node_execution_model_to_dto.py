"""Map NodeExecution persistence models to application query DTOs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from shell.execution_service.application.execution.node_execution.dto.node_execution_dto import (
    NodeExecutionDto,
)

if TYPE_CHECKING:
    from shell.execution_service.infrastructure.execution.node_execution.persistence.sql.models.node_execution import (
        NodeExecutionModel,
    )


def node_execution_model_to_dto(model: NodeExecutionModel) -> NodeExecutionDto:
    return NodeExecutionDto(
        id=model.id,
        node_type=model.node_type,
    )
