from __future__ import annotations

from pydantic import BaseModel, Field


class SemanticQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    purpose: str | None = Field(None, max_length=1000)
    limit: int = Field(default=1, ge=1)
    default_graph_definition_id: str | None = Field(None, max_length=255)
