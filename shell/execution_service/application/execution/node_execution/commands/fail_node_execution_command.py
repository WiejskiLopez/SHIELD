from __future__ import annotations

from dataclasses import dataclass

from shell.platform.application.commands.command import Command
from shell.platform.application.exceptions.command_validation_error import RequiredCommandFieldError


@dataclass(frozen=True, slots=True)
class FailNodeExecutionCommand(Command):
    node_execution_id: str

    def __post_init__(self) -> None:
        if not self.node_execution_id:
            raise RequiredCommandFieldError("node_execution_id")
