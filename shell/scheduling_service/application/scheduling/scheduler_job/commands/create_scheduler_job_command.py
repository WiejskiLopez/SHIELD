from __future__ import annotations

from dataclasses import dataclass

from shell.platform.application.commands.command import Command
from shell.platform.application.exceptions.command_validation_error import RequiredCommandFieldError


@dataclass(frozen=True, slots=True)
class CreateSchedulerJobCommand(Command):
    scheduler_definition_id: str
    name: str
    job_type: str = "messaging"
    interval_seconds: float = 1.0
    batch_size: int = 50
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.scheduler_definition_id:
            raise RequiredCommandFieldError("scheduler_definition_id")
        if not self.name:
            raise RequiredCommandFieldError("name")
