from __future__ import annotations

from shell.execution_service.domain.execution.aggregates.node_execution.node_execution import (
    NodeExecution,
)
from shell.execution_service.domain.execution.aggregates.node_execution.repositories.node_execution_repository import (
    NodeExecutionRepository,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_execution_id import (
    NodeExecutionId,
)
from shell.platform.infrastructure.persistence.in_memory_repository import (
    InMemoryRepository,
)


class InMemoryNodeExecutionRepository(
    InMemoryRepository[NodeExecution, NodeExecutionId], NodeExecutionRepository
):
    async def get_by_id(self, id: NodeExecutionId) -> NodeExecution | None:
        node = self._store.get(id.value)
        if node is None or node.deleted_at.value is not None:
            return None
        return node

    async def list_by_ids(self, ids: list[NodeExecutionId]) -> list[NodeExecution]:
        nodes: list[NodeExecution] = []
        for node_id in ids:
            node = await self.get_by_id(node_id)
            if node is not None:
                nodes.append(node)
        return nodes

    async def save(self, node: NodeExecution) -> None:
        self._store[node.id.value] = node
