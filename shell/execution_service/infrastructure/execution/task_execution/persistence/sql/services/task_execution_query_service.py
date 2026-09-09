from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.sql import func

from shell.execution_service.infrastructure.execution.task_execution.persistence.sql.mappers.task_execution_model_to_dto import (
    task_execution_model_to_dto,
)
from shell.execution_service.infrastructure.execution.task_execution.persistence.sql.models import (
    TaskExecutionModel,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from shell.execution_service.application.execution.task_execution.dto.task_execution_dto import (
        TaskExecutionDto,
    )


class TaskExecutionQueryService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_by_id(self, task_execution_id: str) -> TaskExecutionDto | None:
        async with self._session_factory() as session:
            stmt = select(TaskExecutionModel).where(TaskExecutionModel.id == task_execution_id)
            res = await session.execute(stmt)
            model = res.scalar_one_or_none()
            if not model:
                return None
            return task_execution_model_to_dto(model)

    async def list_all(
        self, *, page: int = 1, page_size: int = 100
    ) -> tuple[list[TaskExecutionDto], int]:
        async with self._session_factory() as session:
            count_stmt = select(func.count()).select_from(TaskExecutionModel)
            total = (await session.execute(count_stmt)).scalar_one()

            offset = (page - 1) * page_size
            stmt = (
                select(TaskExecutionModel)
                .order_by(TaskExecutionModel.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
            rows = (await session.execute(stmt)).scalars().all()

            dtos = [task_execution_model_to_dto(row) for row in rows]
            return dtos, total

    async def get_task_execution_by_name(self, name: str) -> TaskExecutionDto | None:
        async with self._session_factory() as session:
            stmt = (
                select(TaskExecutionModel)
                .where(TaskExecutionModel.name == name)
                .order_by(TaskExecutionModel.id)
                .limit(1)
            )
            res = await session.execute(stmt)
            model = res.scalar_one_or_none()
            if not model:
                return None

            return task_execution_model_to_dto(model)

    async def get_current_task(self, name: str) -> TaskExecutionDto | None:
        return await self.get_task_execution_by_name(name)
