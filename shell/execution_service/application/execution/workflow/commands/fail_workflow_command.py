from __future__ import annotations

from dataclasses import dataclass

from shell.platform.application.commands.command import Command
from shell.platform.application.exceptions.command_validation_error import RequiredCommandFieldError


@dataclass(frozen=True, slots=True)
class FailWorkflowCommand(Command):
    workflow_id: str

    def __post_init__(self) -> None:
        if not self.workflow_id:
            raise RequiredCommandFieldError("workflow_id")
