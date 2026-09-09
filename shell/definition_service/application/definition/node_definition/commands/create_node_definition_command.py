from __future__ import annotations

from dataclasses import dataclass

from shell.platform.application.commands.command import Command
from shell.platform.application.exceptions.command_validation_error import (
    RequiredCommandFieldError,
)


@dataclass(frozen=True, slots=True)
class CreateNodeDefinitionCommand(Command):
    node_type: str
    node_position: int
    max_step: int | None = None

    def __post_init__(self) -> None:
        if not self.node_type:
            raise RequiredCommandFieldError("node_type")
