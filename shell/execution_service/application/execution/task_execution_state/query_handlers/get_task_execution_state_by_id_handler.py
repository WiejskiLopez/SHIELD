from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shell.execution_service.application.execution.task_execution.dto.task_execution_state_dto import (
        TaskExecutionStateDto,
    )
    from shell.execution_service.application.execution.task_execution_state.ports.task_execution_state_query_service import (
        TaskExecutionStateQueryService,
    )
    from shell.execution_service.application.execution.task_execution_state.queries.get_task_execution_state_by_id_query import (
        GetTaskExecutionStateByIdQuery,
    )


class GetTaskExecutionStateByIdHandler:
    def __init__(self, queries: TaskExecutionStateQueryService) -> None:
        self._queries = queries

    async def handle(
        self, query: GetTaskExecutionStateByIdQuery
    ) -> TaskExecutionStateDto | None:
        return await self._queries.get_by_id(query.task_execution_state_id)