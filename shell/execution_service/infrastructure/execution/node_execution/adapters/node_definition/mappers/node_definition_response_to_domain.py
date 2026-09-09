from __future__ import annotations

from typing import TYPE_CHECKING

from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_definition_id_ref import (
    NodeDefinitionIdRef,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_definition_reference import (
    NodeDefinitionReference,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_position import (
    NodePosition,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_type import (
    NodeType,
)

if TYPE_CHECKING:
    from shell.execution_service.infrastructure.execution.node_execution.adapters.node_definition.contracts.v1.node_definition_response import (
        NodeDefinitionResponseV1,
    )


def node_definition_response_to_domain(
    response: NodeDefinitionResponseV1,
) -> NodeDefinitionReference:
    return NodeDefinitionReference(
        node_definition_id=NodeDefinitionIdRef(response.id),
        node_type=NodeType(response.node_type),
        node_position=NodePosition(response.node_position),
    )
