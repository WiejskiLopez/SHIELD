from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_definition_id_ref import (
    NodeDefinitionIdRef,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_definition_reference import (
    NodeDefinitionReference,
)
from shell.execution_service.infrastructure.execution.node_execution.adapters.node_definition.node_definition_reader_http_adapter import (
    NodeDefinitionReaderHttpAdapter,
)


class TestNodeDefinitionReaderHttpAdapter:
    async def test_get_definition_maps_response_and_fetches_fresh_data(
        self,
    ) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            side_effect=(
                Mock(
                    status_code=200,
                    json=Mock(
                        return_value={
                            "id": "node-1",
                            "node_type": "task",
                            "node_position": 2,
                        }
                    ),
                ),
                Mock(
                    status_code=200,
                    json=Mock(
                        return_value={
                            "id": "node-1",
                            "node_type": "condition",
                            "node_position": 3,
                        }
                    ),
                ),
            )
        )
        adapter = NodeDefinitionReaderHttpAdapter(client)

        first = await adapter.get_node_definition(NodeDefinitionIdRef("node-1"))
        second = await adapter.get_node_definition(NodeDefinitionIdRef("node-1"))

        assert isinstance(first, NodeDefinitionReference)
        assert isinstance(second, NodeDefinitionReference)
        assert first.node_type.value == "task"
        assert second.node_type.value == "condition"
        assert client.get.await_count == 2

    async def test_get_definition_propagates_server_errors(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value=Mock(
                status_code=503,
                raise_for_status=Mock(side_effect=RuntimeError("definition unavailable")),
            )
        )
        adapter = NodeDefinitionReaderHttpAdapter(client)

        with pytest.raises(RuntimeError, match="definition unavailable"):
            await adapter.get_node_definition(NodeDefinitionIdRef("node-1"))
