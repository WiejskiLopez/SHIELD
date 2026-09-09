from __future__ import annotations

from pydantic import BaseModel


class CreateNodeDefinitionResponse(BaseModel):
    id: str
