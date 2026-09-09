"""Outbox e2e: mutacja FSM EdgeExecution przez save() musi zostawić dokładnie 1 wiersz w event_outbox."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from shell.execution_service.domain.execution.aggregates.edge_execution.edge_execution import (
    EdgeExecution,
)
from shell.execution_service.domain.execution.aggregates.edge_execution.repositories.edge_execution_repository import (
    EdgeExecutionRepository,
)
from shell.execution_service.domain.execution.aggregates.edge_execution.value_objects.edge_definition_id_ref import (
    EdgeDefinitionIdRef,
)
from shell.execution_service.domain.execution.aggregates.edge_execution.value_objects.edge_execution_id import (
    EdgeExecutionId,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_execution_id import (
    NodeExecutionId,
)
from shell.execution_service.infrastructure.execution.edge_execution.persistence.sql.unit_of_work import (
    SqlAlchemyEdgeExecutionUnitOfWork,
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


def _edge(edge_id: str) -> EdgeExecution:
    edge = EdgeExecution.create(
        id_=EdgeExecutionId(edge_id),
        source_node_execution_id=NodeExecutionId("source-1"),
        edge_definition_id=EdgeDefinitionIdRef("edge-def-1"),
        now=CreatedAt.from_datetime(_NOW_DT),
    )
    edge.pull_events()
    return edge


class TestEdgeExecutionOutbox:
    async def test_delete_writes_one_outbox_row(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyEdgeExecutionUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            edge = _edge("outbox-edge-delete")
            edge.delete(now=_OCCURRED)
            await uow.save(EdgeExecutionRepository, edge)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("edge_execution_id") == "outbox-edge-delete"]
        assert len(rows) == 1, f"expected exactly 1 outbox row, got {len(rows)}"
        assert rows[0].payload.get("edge_execution_id") == "outbox-edge-delete"
        assert rows[0].integration_event_name == "EdgeExecutionDeletedIntegrationEvent"

    async def test_change_target_writes_one_outbox_row(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyEdgeExecutionUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            edge = _edge("outbox-edge-touch")
            edge.pull_events()
            edge.change_target(target_node_execution_id=NodeExecutionId("target-1"), now=_OCCURRED)
            await uow.save(EdgeExecutionRepository, edge)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("edge_execution_id") == "outbox-edge-touch"]
        assert len(rows) == 1
        assert rows[0].payload.get("edge_execution_id") == "outbox-edge-touch"
        assert rows[0].integration_event_name == "EdgeExecutionChangedIntegrationEvent"