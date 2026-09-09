from __future__ import annotations

from shell.platform.application.exceptions.application_error import ApplicationError


class NodeDefinitionNotFoundError(ApplicationError):
    def __init__(self, node_definition_id: str) -> None:
        super().__init__(f"Node definition not found: {node_definition_id!r}")
