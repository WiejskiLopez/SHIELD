from __future__ import annotations

from pydantic import BaseModel, Field


class CreateNodeDefinitionRequest(BaseModel):
    node_type: str = Field(..., min_length=1, max_length=100)
    node_position: int = Field(..., ge=0)
    max_step: int | None = Field(default=None, ge=0)
