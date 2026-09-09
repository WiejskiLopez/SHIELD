from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import exists as sa_exists
from sqlalchemy import select

from shell.execution_service.domain.execution.aggregates.node_execution.repositories.node_execution_repository import (
    NodeExecutionRepository,
)
from shell.execution_service.infrastructure.execution.node_execution.persistence.sql.mappers import (
    node_execution_change_model,
    node_execution_entity_to_model,
    node_execution_model_to_entity,
)
from shell.execution_service.infrastructure.execution.node_execution.persistence.sql.models.node_execution import (
    NodeExecutionModel,
)
from shell.platform.domain.value_objects.exists_result import ExistsResult

if TYPE_CHECKING:
    from sqlalchemy import Select
    from sqlalchemy.ext.asyncio import AsyncSession

    from shell.execution_service.domain.execution.aggregates.node_execution.node_execution import (
        NodeExecution,
    )
    from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_execution_id import (
        NodeExecutionId,
    )

class SqlNodeExecutionRepository(NodeExecutionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self) -> Select[tuple[NodeExecutionModel]]:
        return select(NodeExecutionModel).where(NodeExecutionModel.deleted_at.is_(None))

    async def get_by_id(self, node_id: NodeExecutionId) -> NodeExecution | None:
        query = self._base_query().where(NodeExecutionModel.id == node_id.value)
        row = (await self._session.execute(query)).scalar_one_or_none()
        return node_execution_model_to_entity(row) if row else None

    async def save(self, node: NodeExecution) -> None:
        model = await self._session.get(NodeExecutionModel, node.id.value)
        if model is None:
            self._session.add(node_execution_entity_to_model(node))
        else:
            node_execution_change_model(model, node)

    async def list_by_ids(self, ids: list[NodeExecutionId]) -> list[NodeExecution]:
        if not ids:
            return []
        id_values = [i.value for i in ids]
        query = self._base_query().where(NodeExecutionModel.id.in_(id_values))
        rows = (await self._session.execute(query)).scalars().all()
        return [node_execution_model_to_entity(r) for r in rows if r is not None]

    async def delete(self, id: NodeExecutionId) -> None:
        model = await self._session.get(NodeExecutionModel, id.value)
        if model is not None:
            await self._session.delete(model)

    async def exists(self, id: NodeExecutionId) -> ExistsResult:
        stmt = select(sa_exists().where(NodeExecutionModel.id == id.value))
        result = await self._session.execute(stmt)
        return ExistsResult(result.scalar() or False)
