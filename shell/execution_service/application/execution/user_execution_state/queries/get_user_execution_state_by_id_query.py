from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GetUserExecutionStateByIdQuery:
    user_execution_state_id: str