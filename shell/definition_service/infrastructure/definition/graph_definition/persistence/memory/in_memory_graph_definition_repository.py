from __future__ import annotations

from shell.definition_service.domain.definition.aggregates.graph_definition.graph_definition import (
    GraphDefinition,
)
from shell.definition_service.domain.definition.aggregates.graph_definition.repositories import (
    GraphDefinitionRepository,
)
from shell.definition_service.domain.definition.aggregates.graph_definition.value_objects import (
    GraphDefinitionId,
)
from shell.platform.infrastructure.persistence.in_memory_repository import InMemoryRepository


class InMemoryGraphDefinitionRepository(
    InMemoryRepository[GraphDefinition, GraphDefinitionId], GraphDefinitionRepository
):
    async def get_by_id(self, id: GraphDefinitionId) -> GraphDefinition | None:
        return await super().get_by_id(id)

    async def list_all(self) -> list[GraphDefinition]:
        return [graph for graph in self._store.values() if not self._is_deleted(graph)]
