from __future__ import annotations

from pydantic import BaseModel


class NodeDefinitionResponse(BaseModel):
    id: str
    node_type: str
    node_position: int
