from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.sql import func

from shell.execution_service.infrastructure.execution.workflow.persistence.sql.mappers.workflow_model_to_dto import (
    workflow_model_to_dto,
)
from shell.execution_service.infrastructure.execution.workflow.persistence.sql.models import (
    WorkflowModel,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from shell.execution_service.application.execution.workflow.dto.workflow_dto import (
        WorkflowDto,
    )


class WorkflowQueryService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_by_id(self, workflow_id: str) -> WorkflowDto | None:
        async with self._session_factory() as session:
            stmt = select(WorkflowModel).where(WorkflowModel.id == workflow_id)
            res = await session.execute(stmt)
            model = res.scalar_one_or_none()
            if not model:
                return None
            return workflow_model_to_dto(model)

    async def list_all(
        self,
        *,
        page: int = 1,
        page_size: int = 100,
        status: str | None = None,
    ) -> tuple[list[WorkflowDto], int]:
        async with self._session_factory() as session:
            base_stmt = select(WorkflowModel)
            if status is not None:
                base_stmt = base_stmt.where(WorkflowModel.status == status)

            count_stmt = select(func.count()).select_from(base_stmt.subquery())
            total = (await session.execute(count_stmt)).scalar_one()

            offset = (page - 1) * page_size
            stmt = (
                base_stmt.order_by(WorkflowModel.created_at.desc()).offset(offset).limit(page_size)
            )
            rows = (await session.execute(stmt)).scalars().all()

            dtos = [workflow_model_to_dto(r) for r in rows]
            return dtos, total
