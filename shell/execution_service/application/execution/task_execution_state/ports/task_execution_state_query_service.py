from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from shell.execution_service.application.execution.task_execution.dto.task_execution_state_dto import (
        TaskExecutionStateDto,
    )


class TaskExecutionStateQueryService(Protocol):
    async def get_by_id(self, task_execution_state_id: str) -> TaskExecutionStateDto | None: ...