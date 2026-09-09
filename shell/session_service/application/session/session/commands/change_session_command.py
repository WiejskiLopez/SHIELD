from __future__ import annotations

from dataclasses import dataclass

from shell.platform.application.commands.command import Command
from shell.platform.application.exceptions.command_validation_error import RequiredCommandFieldError


@dataclass(frozen=True, slots=True)
class ChangeSessionCommand(Command):
    session_id: str

    def __post_init__(self) -> None:
        if not self.session_id:
            raise RequiredCommandFieldError("session_id")
