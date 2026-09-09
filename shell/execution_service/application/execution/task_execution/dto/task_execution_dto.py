from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class TaskExecutionDto:
    id: str
    created_at: datetime
    name: str
    work_dir: str
    workflow_id: str
    changed_at: datetime | None = None
    deleted_at: datetime | None = None
