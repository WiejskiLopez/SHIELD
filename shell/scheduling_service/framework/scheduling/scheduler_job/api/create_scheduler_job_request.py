from __future__ import annotations

from pydantic import BaseModel, Field


class CreateSchedulerJobRequest(BaseModel):
    scheduler_definition_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    job_type: str = Field("messaging", min_length=1, max_length=100)
    interval_seconds: float = Field(1.0, gt=0)
    batch_size: int = Field(50, ge=1, le=1000)
    enabled: bool = True
