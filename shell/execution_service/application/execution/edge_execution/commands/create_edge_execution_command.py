from __future__ import annotations

from dataclasses import dataclass

from shell.platform.application.commands.command import Command
from shell.platform.application.exceptions.command_validation_error import RequiredCommandFieldError


@dataclass(frozen=True, slots=True)
class CreateEdgeExecutionCommand(Command):
    edge_definition_id: str
    source_node_execution_id: str
    target_node_execution_id: str | None = None

    def __post_init__(self) -> None:
        if not self.edge_definition_id:
            raise RequiredCommandFieldError("edge_definition_id")
        if not self.source_node_execution_id:
            raise RequiredCommandFieldError("source_node_execution_id")
