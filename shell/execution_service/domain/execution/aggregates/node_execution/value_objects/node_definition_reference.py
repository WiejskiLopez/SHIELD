from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from shell.platform.domain.base.value_object import ValueObject

if TYPE_CHECKING:
    from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_definition_id_ref import (
        NodeDefinitionIdRef,
    )
    from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_position import (
        NodePosition,
    )
    from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_type import (
        NodeType,
    )


@dataclass(frozen=True, slots=True)
class NodeDefinitionReference(ValueObject):
    node_definition_id: NodeDefinitionIdRef
    node_type: NodeType
    node_position: NodePosition
