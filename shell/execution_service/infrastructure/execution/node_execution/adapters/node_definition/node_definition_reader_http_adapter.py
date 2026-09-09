from __future__ import annotations

from typing import TYPE_CHECKING

from shell.execution_service.domain.execution.aggregates.node_execution.ports.node_definition_reader import (
    NodeDefinitionReader,
)
from shell.execution_service.infrastructure.execution.node_execution.adapters.node_definition.contracts.v1.node_definition_response import (
    NodeDefinitionResponseV1,
)
from shell.execution_service.infrastructure.execution.node_execution.adapters.node_definition.mappers.node_definition_response_to_domain import (
    node_definition_response_to_domain,
)

if TYPE_CHECKING:
    import httpx

    from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_definition_id_ref import (
        NodeDefinitionIdRef,
    )
    from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_definition_reference import (
        NodeDefinitionReference,
    )


class NodeDefinitionReaderHttpAdapter(NodeDefinitionReader):
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def get_node_definition(
        self,
        node_definition_id: NodeDefinitionIdRef,
    ) -> NodeDefinitionReference | None:
        response = await self._client.get(
            f"/api/v1/node-definitions/{node_definition_id.value}"
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return node_definition_response_to_domain(
            NodeDefinitionResponseV1.model_validate(response.json())
        )
