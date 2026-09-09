from __future__ import annotations

from dataclasses import dataclass

from shell.platform.application.commands.command import Command
from shell.platform.application.exceptions.command_validation_error import (
    InvalidCommandFieldError,
    RequiredCommandFieldError,
)


@dataclass(frozen=True, slots=True)
class ReleaseScheduleCommand(Command):
    """Kompensacja kroku provision_schedule."""

    scheduler_job_id: str
    attempt: int = 1

    def __post_init__(self) -> None:
        if not self.scheduler_job_id:
            raise RequiredCommandFieldError("scheduler_job_id")
        if self.attempt < 1:
            raise InvalidCommandFieldError("attempt", "must be >= 1")
