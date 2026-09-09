from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from shell.execution_service.infrastructure.execution.graph_execution.persistence.sql.mappers.graph_execution_model_to_dto import (
    graph_execution_model_to_dto,
)
from shell.execution_service.infrastructure.execution.graph_execution.persistence.sql.models.graph_execution import (
    GraphExecutionModel,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from shell.execution_service.application.execution.graph_execution.dto.graph_execution_dto import (
        GraphExecutionDto,
    )


class GraphExecutionQueryService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_by_id(self, graph_execution_id: str) -> GraphExecutionDto | None:
        async with self._session_factory() as session:
            stmt = select(GraphExecutionModel).where(GraphExecutionModel.id == graph_execution_id)
            res = await session.execute(stmt)
            model = res.scalar_one_or_none()
            if not model:
                return None
            return graph_execution_model_to_dto(model)
