from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from shell.execution_service.domain.execution.aggregates.node_execution.node_execution import (
        NodeExecution,
    )
    from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_execution_id import (
        NodeExecutionId,
    )
    from shell.platform.domain.value_objects.exists_result import ExistsResult


class NodeExecutionRepository(Protocol):
    async def get_by_id(self, node_id: NodeExecutionId) -> NodeExecution | None: ...

    async def delete(self, id: NodeExecutionId) -> None: ...
    async def exists(self, id: NodeExecutionId) -> ExistsResult: ...

    async def save(self, node: NodeExecution) -> None: ...

    async def list_by_ids(self, ids: list[NodeExecutionId]) -> list[NodeExecution]: ...
