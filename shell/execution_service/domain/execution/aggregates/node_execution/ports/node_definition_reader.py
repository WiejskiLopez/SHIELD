from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_definition_id_ref import (
        NodeDefinitionIdRef,
    )
    from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_definition_reference import (
        NodeDefinitionReference,
    )


class NodeDefinitionReader(Protocol):
    async def get_node_definition(
        self,
        node_definition_id: NodeDefinitionIdRef,
    ) -> NodeDefinitionReference | None: ...
