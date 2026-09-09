from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class ChangeProjectRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=500)
    repo_url: HttpUrl | None = Field(None, max_length=2048)
