from __future__ import annotations

from dataclasses import dataclass

from shell.platform.application.commands.command import Command
from shell.platform.application.exceptions.command_validation_error import (
    InvalidCommandFieldError,
    RequiredCommandFieldError,
)


@dataclass(frozen=True, slots=True)
class ProvisionWorkspaceCommand(Command):
    """Krok sagi — dostarczany przez komendę delivery do serwisu docelowego."""

    project_id: str
    fail: bool = False
    attempt: int = 1

    def __post_init__(self) -> None:
        if not self.project_id:
            raise RequiredCommandFieldError("project_id")
        if self.attempt < 1:
            raise InvalidCommandFieldError("attempt", "must be >= 1")
