from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from shell.definition_service.domain.definition.aggregates.node_definition.repositories import (
    NodeDefinitionRepository,
)
from shell.definition_service.infrastructure.definition.node_definition.persistence.sql.models import (
    NodeDefinitionModel,
)
from shell.definition_service.infrastructure.definition.node_link_definition.persistence.sql.models import (
    NodeLinkDefinitionModel,
)
from shell.platform.domain.value_objects.created_at import CreatedAt
from shell.platform.domain.value_objects.exists_result import ExistsResult

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from shell.definition_service.domain.definition.aggregates.graph_definition.value_objects.graph_definition_id import (
        GraphDefinitionId,
    )


from shell.definition_service.domain.definition.aggregates.node_definition.node_definition import (
    NodeDefinition,
)
from shell.definition_service.domain.definition.aggregates.node_definition.value_objects.max_step import (
    MaxStep,
)
from shell.definition_service.domain.definition.aggregates.node_definition.value_objects.node_definition_id import (
    NodeDefinitionId,
)
from shell.definition_service.domain.definition.aggregates.node_definition.value_objects.node_position import (
    NodePosition,
)
from shell.definition_service.domain.definition.aggregates.node_definition.value_objects.node_type import (
    NodeType,
)


class SqlNodeDefinitionRepository(NodeDefinitionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self,
        node_definition_id: NodeDefinitionId,
    ) -> NodeDefinition | None:

        stmt = select(NodeDefinitionModel).where(
            NodeDefinitionModel.id == node_definition_id.value,
            NodeDefinitionModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is None:
            return None
        return self._model_to_entity(model)

    async def list_by_graph_definition_id(
        self,
        graph_definition_id: GraphDefinitionId,
    ) -> list[NodeDefinition]:

        stmt = (
            select(NodeDefinitionModel)
            .join(
                NodeLinkDefinitionModel,
                NodeLinkDefinitionModel.node_definition_id == NodeDefinitionModel.id,
            )
            .where(
                NodeLinkDefinitionModel.graph_definition_id == graph_definition_id.value,
                NodeLinkDefinitionModel.deleted_at.is_(None),
                NodeDefinitionModel.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(m) for m in models]

    async def save(self, node_definition: NodeDefinition) -> None:
        model = await self._session.get(
            NodeDefinitionModel,
            node_definition.id.value,
        )
        if model is None:
            model = self._entity_to_model(node_definition)
            self._session.add(model)
        else:
            self._change_model(model, node_definition)

    async def delete(self, id: NodeDefinitionId) -> None:
        model = await self._session.get(NodeDefinitionModel, id.value)
        if model is not None:
            await self._session.delete(model)

    async def exists(self, id: NodeDefinitionId) -> ExistsResult:
        stmt = select(NodeDefinitionModel.id).where(
            NodeDefinitionModel.id == id.value,
            NodeDefinitionModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return ExistsResult(model is not None)

    def _model_to_entity(
        self,
        model: NodeDefinitionModel,
    ) -> NodeDefinition:
        return NodeDefinition(
            id=NodeDefinitionId(model.id),
            created_at=CreatedAt.from_datetime(model.created_at),
            node_position=NodePosition(model.node_position),
            node_type=NodeType(model.node_type),
            max_step=MaxStep(model.max_step) if model.max_step is not None else None,
        )

    def _entity_to_model(self, entity: NodeDefinition) -> NodeDefinitionModel:
        return NodeDefinitionModel(
            id=entity.id.value,
            node_position=entity.node_position.value,
            node_type=entity.node_type.value,
            max_step=entity.max_step.value if entity.max_step is not None else None,
            created_at=entity.created_at.value,
            changed_at=entity.changed_at.value,
            deleted_at=entity.deleted_at.value,
        )

    def _change_model(self, model: NodeDefinitionModel, entity: NodeDefinition) -> None:
        model.node_position = entity.node_position.value
        model.node_type = entity.node_type.value
        model.max_step = entity.max_step.value if entity.max_step is not None else None
