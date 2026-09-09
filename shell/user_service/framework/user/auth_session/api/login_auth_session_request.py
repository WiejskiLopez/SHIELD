from __future__ import annotations

from pydantic import BaseModel, Field


class LoginAuthSessionRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
