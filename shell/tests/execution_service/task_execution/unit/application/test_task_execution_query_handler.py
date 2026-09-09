"""Unit tests for task_execution query handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from shell.execution_service.application.execution.task_execution.queries import (
    GetTaskExecutionCurrentQuery,
)
from shell.execution_service.application.execution.task_execution.query_handlers.get_task_execution_current_handler import (
    GetTaskExecutionCurrentHandler,
)

if TYPE_CHECKING:
    from shell.execution_service.infrastructure.execution.task_execution.persistence.memory.in_memory_task_execution_query_service import (
        InMemoryTaskExecutionQueryService,
    )


class TestTaskExecutionQueryHandler:
    async def test_get_task_not_found(self, queries: InMemoryTaskExecutionQueryService) -> None:
        dto = await GetTaskExecutionCurrentHandler(queries).handle(  # type: ignore[arg-type]
            GetTaskExecutionCurrentQuery("missing")
        )
        assert dto is None
