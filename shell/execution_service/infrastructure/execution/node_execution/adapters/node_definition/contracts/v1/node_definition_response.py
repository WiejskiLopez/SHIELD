from __future__ import annotations

from pydantic import BaseModel


class NodeDefinitionResponseV1(BaseModel):
    id: str
    node_type: str
    node_position: int
