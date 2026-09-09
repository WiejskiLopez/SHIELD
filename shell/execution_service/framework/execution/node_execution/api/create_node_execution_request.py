from __future__ import annotations

from pydantic import BaseModel, Field


class CreateNodeExecutionRequest(BaseModel):
    graph_execution_id: str = Field(..., min_length=1, max_length=255)
    node_definition_id: str = Field(..., min_length=1, max_length=255)
