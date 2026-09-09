from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from shell.execution_service.infrastructure.execution.node_execution.persistence.sql.mappers.node_execution_model_to_dto import (
    node_execution_model_to_dto,
)
from shell.execution_service.infrastructure.execution.node_execution.persistence.sql.models.node_execution import (
    NodeExecutionModel,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from shell.execution_service.application.execution.node_execution.dto.node_execution_dto import (
        NodeExecutionDto,
    )


class NodeExecutionQueryService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_by_id(self, node_execution_id: str) -> NodeExecutionDto | None:
        async with self._session_factory() as session:
            stmt = select(NodeExecutionModel).where(NodeExecutionModel.id == node_execution_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return node_execution_model_to_dto(model)