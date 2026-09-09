from __future__ import annotations

from typing import TYPE_CHECKING

from shell.execution_service.infrastructure.execution.node_execution.persistence.sql.models.node_execution import (
    NodeExecutionModel,
)

if TYPE_CHECKING:
    from shell.execution_service.domain.execution.aggregates.node_execution.node_execution import (
        NodeExecution,
    )


def node_execution_entity_to_model(node: NodeExecution) -> NodeExecutionModel:
    return NodeExecutionModel(
        id=node.id.value,
        position=node.node_position.value,
        node_type=node.node_type.value,
        node_definition_id=node.node_definition_id.value,
        created_at=node.created_at.value,
        changed_at=node.changed_at.value,
        deleted_at=node.deleted_at.value,
        status=node.status.value,
    )
