from __future__ import annotations

from pydantic import BaseModel, Field


class CreateSchedulerExecutionRequest(BaseModel):
    scheduler_definition_id: str = Field(..., min_length=1, max_length=255)
