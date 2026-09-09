from __future__ import annotations

from pydantic import BaseModel, Field


class CreateWorkflowRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=255)
    project_id: str = Field(..., min_length=1, max_length=255)
