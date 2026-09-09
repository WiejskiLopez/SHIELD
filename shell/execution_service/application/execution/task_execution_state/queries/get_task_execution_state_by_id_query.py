from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GetTaskExecutionStateByIdQuery:
    task_execution_state_id: str