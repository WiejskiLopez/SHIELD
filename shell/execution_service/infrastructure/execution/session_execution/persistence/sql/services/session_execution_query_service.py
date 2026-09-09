from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from shell.execution_service.infrastructure.execution.session_execution.persistence.sql.mappers.session_execution_model_to_dto import (
    session_execution_model_to_dto,
)
from shell.execution_service.infrastructure.execution.session_execution.persistence.sql.models.session_execution import (
    SessionExecutionModel,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from shell.execution_service.application.execution.session_execution.dto.session_execution_dto import (
        SessionExecutionDto,
    )


class SessionExecutionQueryService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_by_id(self, session_execution_id: str) -> SessionExecutionDto | None:
        async with self._session_factory() as session:
            stmt = select(SessionExecutionModel).where(
                SessionExecutionModel.id == session_execution_id
            )
            res = await session.execute(stmt)
            model = res.scalar_one_or_none()
            if model is None:
                return None
            return session_execution_model_to_dto(model)
