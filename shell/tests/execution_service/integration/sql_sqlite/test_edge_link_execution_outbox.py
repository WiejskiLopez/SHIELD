"""Outbox e2e: mutacja FSM EdgeLinkExecution przez save() musi zostawić dokładnie 1 wiersz w event_outbox."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from shell.execution_service.domain.execution.aggregates.edge_execution.value_objects.edge_execution_id import (
    EdgeExecutionId,
)
from shell.execution_service.domain.execution.aggregates.edge_link_execution.edge_link_execution import (
    EdgeLinkExecution,
)
from shell.execution_service.domain.execution.aggregates.edge_link_execution.repositories.edge_link_execution_repository import (
    EdgeLinkExecutionRepository,
)
from shell.execution_service.domain.execution.aggregates.edge_link_execution.value_objects.edge_link_execution_id import (
    EdgeLinkExecutionId,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_execution_id import (
    NodeExecutionId,
)
from shell.execution_service.infrastructure.execution.edge_link_execution.persistence.sql.unit_of_work import (
    SqlAlchemyEdgeLinkExecutionUnitOfWork,
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


def _link(link_id: str) -> EdgeLinkExecution:
    link = EdgeLinkExecution.create(
        id_=EdgeLinkExecutionId(link_id),
        node_execution_id=NodeExecutionId("node-1"),
        edge_execution_id=EdgeExecutionId("edge-1"),
        now=CreatedAt.from_datetime(_NOW_DT),
    )
    link.pull_events()
    return link


class TestEdgeLinkExecutionOutbox:
    async def test_delete_writes_one_outbox_row(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyEdgeLinkExecutionUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            link = _link("outbox-link-delete")
            link.delete(now=_OCCURRED)
            await uow.save(EdgeLinkExecutionRepository, link)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("edge_link_execution_id") == "outbox-link-delete"]
        assert len(rows) == 1, f"expected exactly 1 outbox row, got {len(rows)}"
        assert rows[0].payload.get("edge_link_execution_id") == "outbox-link-delete"
        assert rows[0].integration_event_name == "EdgeLinkExecutionDeletedIntegrationEvent"

    async def test_touch_writes_one_outbox_row(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyEdgeLinkExecutionUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            link = _link("outbox-link-touch")
            link.pull_events()
            link.touch(now=_OCCURRED)
            await uow.save(EdgeLinkExecutionRepository, link)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("edge_link_execution_id") == "outbox-link-touch"]
        assert len(rows) == 1
        assert rows[0].payload.get("edge_link_execution_id") == "outbox-link-touch"
        assert rows[0].integration_event_name == "EdgeLinkExecutionChangedIntegrationEvent"