from __future__ import annotations

from dataclasses import dataclass

from shell.platform.application.commands.command import Command
from shell.platform.application.exceptions.command_validation_error import RequiredCommandFieldError


@dataclass(frozen=True, slots=True)
class StartProjectProvisionCommand(Command):
    """Inicjalizator sagi — każde wystąpienie tworzy nową instancję projektu."""

    project_id: str
    fail: bool = False

    def __post_init__(self) -> None:
        if not self.project_id:
            raise RequiredCommandFieldError("project_id")
