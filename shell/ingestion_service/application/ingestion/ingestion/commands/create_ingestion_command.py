from __future__ import annotations

from dataclasses import dataclass

from shell.platform.application.commands.command import Command
from shell.platform.application.exceptions.command_validation_error import RequiredCommandFieldError


@dataclass(frozen=True, slots=True)
class CreateIngestionCommand(Command):
    ingestion_data: str
    ingestion_context: str

    def __post_init__(self) -> None:
        if not self.ingestion_data:
            raise RequiredCommandFieldError("ingestion_data")
        if not self.ingestion_context:
            raise RequiredCommandFieldError("ingestion_context")
