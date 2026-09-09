from __future__ import annotations

import json
from typing import TYPE_CHECKING

from sqlalchemy import select

from shell.execution_service.application.execution.user_execution.dto.user_execution_state_dto import (
    UserExecutionStateDto,
)
from shell.execution_service.infrastructure.execution.user_execution_state.persistence.sql.models.user_execution_state import (
    UserExecutionStateModel,
)
from shell.platform.types import JsonStr

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class UserExecutionStateQueryService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_by_id(self, user_execution_state_id: str) -> UserExecutionStateDto | None:
        async with self._session_factory() as session:
            stmt = select(UserExecutionStateModel).where(
                UserExecutionStateModel.id == user_execution_state_id
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return UserExecutionStateDto(
                id=model.id,
                user_execution_id=model.user_execution_id,
                direction=model.direction,
                state_data=JsonStr(json.dumps(dict(model.state_data))),
                created_at=model.created_at,
            )