from __future__ import annotations

from pydantic import BaseModel, Field


class ChangeUserRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
