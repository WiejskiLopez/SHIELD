from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shell.execution_service.domain.execution.aggregates.node_execution.node_execution import (
        NodeExecution,
    )
    from shell.execution_service.infrastructure.execution.node_execution.persistence.sql.models.node_execution import (
        NodeExecutionModel,
    )


def node_execution_change_model(model: NodeExecutionModel, node: NodeExecution) -> None:
    model.position = node.node_position.value
    model.node_type = node.node_type.value
    model.node_definition_id = node.node_definition_id.value
    model.created_at = node.created_at.value
    model.changed_at = node.changed_at.value
    model.deleted_at = node.deleted_at.value
    model.status = node.status.value
