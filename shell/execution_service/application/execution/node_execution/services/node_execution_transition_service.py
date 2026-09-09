from __future__ import annotations

from typing import TYPE_CHECKING

from shell.execution_service.application.execution.node_execution.exceptions.node_execution_not_found_error import (
    NodeExecutionNotFoundError,
)
from shell.execution_service.domain.execution.aggregates.node_execution.repositories.node_execution_repository import (
    NodeExecutionRepository,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_execution_id import (
    NodeExecutionId,
)
from shell.platform.domain.value_objects.occurred_at import OccurredAt

if TYPE_CHECKING:
    from collections.abc import Callable

    from shell.execution_service.domain.execution.aggregates.node_execution.node_execution import (
        NodeExecution,
    )
    from shell.platform.application.ports.persistence.unit_of_work import UnitOfWork
    from shell.platform.domain.ports.time import Clock


class NodeExecutionTransitionService:
    def __init__(self, unit_of_work: UnitOfWork, clock: Clock) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    async def execute(
        self, node_execution_id: str, transition: Callable[[NodeExecution, OccurredAt], None]
    ) -> None:
        aggregate_id = NodeExecutionId(node_execution_id)
        async with self._unit_of_work as unit_of_work:
            node = await unit_of_work.repository(NodeExecutionRepository).get_by_id(aggregate_id)
            if node is None:
                raise NodeExecutionNotFoundError(f"NodeExecution '{node_execution_id}' not found")
            transition(node, OccurredAt.from_datetime(self._clock.now()))
            await unit_of_work.save(NodeExecutionRepository, node)
            await unit_of_work.commit()
