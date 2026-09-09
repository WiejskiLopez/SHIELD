from __future__ import annotations

from pydantic import BaseModel, field_validator

from shell.platform.types import JsonStr


class CreateIngestionRequest(BaseModel):
    ingestion_data: JsonStr
    ingestion_context: JsonStr

    @field_validator("ingestion_data", "ingestion_context")
    @classmethod
    def validate_serialized_payload_size(cls, value: JsonStr) -> JsonStr:
        if len(value.value) > 100_000:
            raise ValueError("JSON payload exceeds the 100000 character limit")
        return value
