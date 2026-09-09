from __future__ import annotations

from typing import TYPE_CHECKING

from shell.execution_service.domain.execution.aggregates.node_link_execution.node_link_execution import (
    NodeLinkExecution,
)
from shell.execution_service.domain.execution.aggregates.node_link_execution.repositories.node_link_execution_repository import (
    NodeLinkExecutionRepository,
)
from shell.execution_service.domain.execution.aggregates.node_link_execution.value_objects.node_link_execution_id import (
    NodeLinkExecutionId,
)
from shell.platform.domain.value_objects.exists_result import ExistsResult
from shell.platform.infrastructure.persistence.in_memory_repository import InMemoryRepository

if TYPE_CHECKING:

    from shell.execution_service.domain.execution.aggregates.graph_execution.value_objects.graph_execution_id import (
        GraphExecutionId,
    )
    from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_execution_id import (
        NodeExecutionId,
    )


class InMemoryNodeLinkExecutionRepository(
    InMemoryRepository[NodeLinkExecution, NodeLinkExecutionId],
    NodeLinkExecutionRepository,
):
    async def get_by_id(
        self,
        node_link_execution_id: NodeLinkExecutionId,
    ) -> NodeLinkExecution | None:
        return await super().get_by_id(node_link_execution_id)

    async def list_by_graph_execution_id(
        self,
        graph_execution_id: GraphExecutionId,
    ) -> list[NodeLinkExecution]:
        return [
            link
            for link in self._visible_values()
            if not self._is_deleted(link) and link.graph_execution_id == graph_execution_id
        ]

    async def list_by_node_execution_id(
        self,
        node_execution_id: NodeExecutionId,
    ) -> list[NodeLinkExecution]:
        return [
            link
            for link in self._visible_values()
            if not self._is_deleted(link) and link.node_execution_id == node_execution_id
        ]

    async def save(self, link: NodeLinkExecution) -> None:
        self._store[link.id.value] = link

    async def delete(self, id: NodeLinkExecutionId) -> None:
           self._store.pop(id.value, None)

    async def exists(self, id: NodeLinkExecutionId) -> ExistsResult:
        return ExistsResult(await self.get_by_id(id) is not None)
