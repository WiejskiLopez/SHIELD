"""Outbox e2e: mutacja FSM GraphExecution przez save() musi zostawić dokładnie 1 wiersz w event_outbox."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from shell.execution_service.domain.execution.aggregates.graph_execution.graph_execution import (
    GraphExecution,
)
from shell.execution_service.domain.execution.aggregates.graph_execution.repositories.graph_execution_repository import (
    GraphExecutionRepository,
)
from shell.execution_service.domain.execution.aggregates.graph_execution.value_objects.graph_depth import (
    GraphDepth,
)
from shell.execution_service.domain.execution.aggregates.graph_execution.value_objects.graph_execution_id import (
    GraphExecutionId,
)
from shell.execution_service.domain.execution.aggregates.graph_execution.value_objects.max_subgraph_depth import (
    MaxSubgraphDepth,
)
from shell.execution_service.domain.execution.aggregates.task_execution.value_objects.task_execution_id import (
    TaskExecutionId,
)
from shell.execution_service.infrastructure.execution.graph_execution.persistence.sql.unit_of_work import (
    SqlAlchemyGraphExecutionUnitOfWork,
)
from shell.execution_service.infrastructure.execution.persistence.sql.models.base import (
    PERSISTENCE_DELIVERY_MODELS,
    OutboxEventModel,
)
from shell.platform.domain.value_objects.created_at import CreatedAt
from shell.platform.domain.value_objects.occurred_at import OccurredAt

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker

_NOW_DT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_NOW = CreatedAt.from_datetime(_NOW_DT)
_OCCURRED = OccurredAt.from_datetime(_NOW_DT)


def _graph(graph_id: str) -> GraphExecution:
    graph = GraphExecution.create_main_round(
        id_=GraphExecutionId(graph_id),
        task_execution_id=TaskExecutionId("task-1"),
        depth=GraphDepth(0),
        max_subgraph_depth=MaxSubgraphDepth(5),
        now=CreatedAt.from_datetime(_NOW_DT),
    )
    graph.pull_events()
    return graph


class TestGraphExecutionOutbox:
    async def test_delete_writes_one_outbox_row(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyGraphExecutionUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            graph = _graph("outbox-graph-delete")
            graph.delete(now=_OCCURRED)
            await uow.save(GraphExecutionRepository, graph)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("graph_execution_id") == "outbox-graph-delete"]
        assert len(rows) == 1, f"expected exactly 1 outbox row, got {len(rows)}"
        assert rows[0].payload.get("graph_execution_id") == "outbox-graph-delete"
        assert rows[0].integration_event_name == "GraphExecutionDeletedIntegrationEvent"