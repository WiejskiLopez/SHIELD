from __future__ import annotations

from typing import TYPE_CHECKING

from shell.definition_service.domain.definition.aggregates.node_link_definition.node_link_definition import (
    NodeLinkDefinition,
)
from shell.definition_service.domain.definition.aggregates.node_link_definition.repositories.node_link_definition_repository import (
    NodeLinkDefinitionRepository,
)
from shell.definition_service.domain.definition.aggregates.node_link_definition.value_objects.node_link_definition_id import (
    NodeLinkDefinitionId,
)
from shell.platform.domain.value_objects.exists_result import ExistsResult
from shell.platform.infrastructure.persistence.in_memory_repository import InMemoryRepository

if TYPE_CHECKING:

    from shell.definition_service.domain.definition.aggregates.graph_definition.value_objects.graph_definition_id import (
        GraphDefinitionId,
    )
    from shell.definition_service.domain.definition.aggregates.node_definition.value_objects.node_definition_id import (
        NodeDefinitionId,
    )


class InMemoryNodeLinkDefinitionRepository(
    InMemoryRepository[NodeLinkDefinition, NodeLinkDefinitionId],
    NodeLinkDefinitionRepository,
):
    async def get_by_id(
        self,
        node_link_definition_id: NodeLinkDefinitionId,
    ) -> NodeLinkDefinition | None:
        return await super().get_by_id(node_link_definition_id)

    async def list_by_graph_definition_id(
        self,
        graph_definition_id: GraphDefinitionId,
    ) -> list[NodeLinkDefinition]:
        return [
            link
            for link in self._visible_values()
            if not self._is_deleted(link) and link.graph_definition_id == graph_definition_id
        ]

    async def list_by_node_definition_id(
        self,
        node_definition_id: NodeDefinitionId,
    ) -> list[NodeLinkDefinition]:
        return [
            link
            for link in self._visible_values()
            if not self._is_deleted(link) and link.node_definition_id == node_definition_id
        ]

    async def save(self, link: NodeLinkDefinition) -> None:
        self._store[link.id.value] = link

    async def delete(self, id: NodeLinkDefinitionId) -> None:
           self._store.pop(id.value, None)

    async def exists(self, id: NodeLinkDefinitionId) -> ExistsResult:
        return ExistsResult(await self.get_by_id(id) is not None)
