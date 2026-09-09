from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shell.execution_service.application.execution.user_execution.dto.user_execution_state_dto import (
        UserExecutionStateDto,
    )
    from shell.execution_service.application.execution.user_execution_state.ports.user_execution_state_query_service import (
        UserExecutionStateQueryService,
    )
    from shell.execution_service.application.execution.user_execution_state.queries.get_user_execution_state_by_id_query import (
        GetUserExecutionStateByIdQuery,
    )


class GetUserExecutionStateByIdHandler:
    def __init__(self, queries: UserExecutionStateQueryService) -> None:
        self._queries = queries

    async def handle(
        self, query: GetUserExecutionStateByIdQuery
    ) -> UserExecutionStateDto | None:
        return await self._queries.get_by_id(query.user_execution_state_id)