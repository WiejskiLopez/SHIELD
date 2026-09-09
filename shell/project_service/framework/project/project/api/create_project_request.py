from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    repo_url: HttpUrl | None = Field(None, max_length=2048)
