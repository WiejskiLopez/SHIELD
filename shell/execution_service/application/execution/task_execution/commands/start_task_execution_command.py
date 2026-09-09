from __future__ import annotations

from dataclasses import dataclass

from shell.platform.application.commands.command import Command
from shell.platform.application.exceptions.command_validation_error import RequiredCommandFieldError


@dataclass(frozen=True, slots=True)
class StartTaskExecutionCommand(Command):
    task_execution_id: str

    def __post_init__(self) -> None:
        if not self.task_execution_id:
            raise RequiredCommandFieldError("task_execution_id")
