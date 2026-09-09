from __future__ import annotations

from typing import TYPE_CHECKING

from shell.execution_service.domain.execution.aggregates.node_execution.node_execution import (
    NodeExecution,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_definition_id_ref import (
    NodeDefinitionIdRef,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_execution_id import (
    NodeExecutionId,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_execution_status import (
    NodeExecutionStatus,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_position import (
    NodePosition,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_type import (
    NodeType,
)
from shell.platform.domain.value_objects.changed_at import NONE_CHANGED_AT, ChangedAt
from shell.platform.domain.value_objects.created_at import CreatedAt
from shell.platform.domain.value_objects.deleted_at import NONE_DELETED_AT, DeletedAt

if TYPE_CHECKING:
    from shell.execution_service.infrastructure.execution.node_execution.persistence.sql.models.node_execution import (
        NodeExecutionModel,
    )


def node_execution_model_to_entity(model: NodeExecutionModel) -> NodeExecution:
    return NodeExecution.restore(
        id=NodeExecutionId(model.id),
        node_position=NodePosition(model.position),
        node_type=NodeType(model.node_type),
        status=NodeExecutionStatus(model.status),
        created_at=CreatedAt.from_datetime(model.created_at),
        changed_at=(
            ChangedAt.from_datetime(model.changed_at)
            if model.changed_at is not None
            else NONE_CHANGED_AT
        ),
        deleted_at=(
            DeletedAt.from_datetime(model.deleted_at)
            if model.deleted_at is not None
            else NONE_DELETED_AT
        ),
        node_definition_id=NodeDefinitionIdRef(model.node_definition_id),
    )
