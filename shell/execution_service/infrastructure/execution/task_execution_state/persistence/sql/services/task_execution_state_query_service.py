from __future__ import annotations

import json
from typing import TYPE_CHECKING

from sqlalchemy import select

from shell.execution_service.application.execution.task_execution.dto.task_execution_state_dto import (
    TaskExecutionStateDto,
)
from shell.execution_service.infrastructure.execution.task_execution_state.persistence.sql.models.task_execution_state import (
    TaskExecutionStateModel,
)
from shell.platform.types import JsonStr

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class TaskExecutionStateQueryService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_by_id(self, task_execution_state_id: str) -> TaskExecutionStateDto | None:
        async with self._session_factory() as session:
            stmt = select(TaskExecutionStateModel).where(
                TaskExecutionStateModel.id == task_execution_state_id
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return TaskExecutionStateDto(
                id=model.id,
                task_execution_id=model.task_execution_id,
                direction=model.direction,
                state_data=JsonStr(json.dumps(dict(model.state_data))),
                created_at=model.created_at,
            )