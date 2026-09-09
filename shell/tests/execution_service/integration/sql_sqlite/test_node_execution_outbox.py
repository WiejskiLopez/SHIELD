"""Outbox e2e: mutacja FSM przez save() musi zostawić dokładnie 1 wiersz w event_outbox."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from shell.execution_service.domain.execution.aggregates.graph_execution.value_objects.graph_execution_id import (
    GraphExecutionId,
)
from shell.execution_service.domain.execution.aggregates.node_execution.node_execution import (
    NodeExecution,
)
from shell.execution_service.domain.execution.aggregates.node_execution.repositories.node_execution_repository import (
    NodeExecutionRepository,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_definition_id_ref import (
    NodeDefinitionIdRef,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_execution_id import (
    NodeExecutionId,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_position import (
    NodePosition,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_type import (
    NodeType,
)
from shell.execution_service.infrastructure.execution.node_execution.persistence.sql.unit_of_work import (
    SqlAlchemyNodeExecutionUnitOfWork,
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


def _node(node_id: str) -> NodeExecution:
    node = NodeExecution.create(
        id=NodeExecutionId(node_id),
        node_type=NodeType("agent"),
        graph_execution_id=GraphExecutionId("graph-1"),
        node_definition_id=NodeDefinitionIdRef("definition-1"),
        node_position=NodePosition(0),
        now=_NOW,
    )
    node.pull_events()
    return node


class TestNodeExecutionOutbox:
    async def test_start_writes_two_outbox_rows(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyNodeExecutionUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            node = _node("outbox-node-start")
            node.start(now=_OCCURRED)
            await uow.save(NodeExecutionRepository, node)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("node_execution_id") == "outbox-node-start"]
        assert len(rows) == 2, f"expected exactly 2 outbox rows, got {len(rows)}"
        assert rows[0].payload.get("node_execution_id") == "outbox-node-start"
        assert rows[0].integration_event_name == "NodeExecutionChangedIntegrationEvent"

    async def test_complete_writes_two_outbox_rows(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyNodeExecutionUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            node = _node("outbox-node-complete")
            node.start(now=_OCCURRED)
            node.pull_events()
            node.complete(now=_OCCURRED)
            await uow.save(NodeExecutionRepository, node)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("node_execution_id") == "outbox-node-complete"]
        assert len(rows) == 2
        assert rows[0].payload.get("node_execution_id") == "outbox-node-complete"
        assert rows[0].integration_event_name == "NodeExecutionChangedIntegrationEvent"

    async def test_fail_writes_two_outbox_rows(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyNodeExecutionUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            node = _node("outbox-node-fail")
            node.start(now=_OCCURRED)
            node.pull_events()
            node.fail(now=_OCCURRED)
            await uow.save(NodeExecutionRepository, node)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("node_execution_id") == "outbox-node-fail"]
        assert len(rows) == 2
        assert rows[0].payload.get("node_execution_id") == "outbox-node-fail"
        assert rows[0].integration_event_name == "NodeExecutionChangedIntegrationEvent"

    async def test_retry_writes_two_outbox_rows(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyNodeExecutionUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            node = _node("outbox-node-retry")
            node.start(now=_OCCURRED)
            node.pull_events()
            node.fail(now=_OCCURRED)
            node.pull_events()
            node.retry(now=_OCCURRED)
            await uow.save(NodeExecutionRepository, node)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("node_execution_id") == "outbox-node-retry"]
        assert len(rows) == 2
        assert rows[0].payload.get("node_execution_id") == "outbox-node-retry"
        assert rows[0].integration_event_name == "NodeExecutionChangedIntegrationEvent"

    async def test_timeout_writes_two_outbox_rows(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyNodeExecutionUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            node = _node("outbox-node-timeout")
            node.start(now=_OCCURRED)
            node.pull_events()
            node.timeout(now=_OCCURRED)
            await uow.save(NodeExecutionRepository, node)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("node_execution_id") == "outbox-node-timeout"]
        assert len(rows) == 2
        assert rows[0].payload.get("node_execution_id") == "outbox-node-timeout"
        assert rows[0].integration_event_name == "NodeExecutionChangedIntegrationEvent"