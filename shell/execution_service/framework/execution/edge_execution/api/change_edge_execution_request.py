from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChangeEdgeExecutionRequest(BaseModel):
    target_node_execution_id: str | None = Field(None, max_length=255)

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return super().model_dump(*args, **kwargs)
