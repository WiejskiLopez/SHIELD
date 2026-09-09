"""Outbox e2e: mutacja FSM Session przez save() musi zostawić dokładnie 1 wiersz w event_outbox."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from shell.platform.domain.value_objects.created_at import CreatedAt
from shell.platform.domain.value_objects.occurred_at import OccurredAt
from shell.session_service.domain.session.aggregates.session.repositories.session_repository import (
    SessionRepository,
)
from shell.session_service.domain.session.aggregates.session.session import Session
from shell.session_service.domain.session.aggregates.session.value_objects.session_id import (
    SessionId,
)
from shell.session_service.domain.session.value_objects.user_id_ref import UserIdRef
from shell.session_service.infrastructure.session.persistence.sql.models.base import (
    PERSISTENCE_DELIVERY_MODELS,
    OutboxEventModel,
)
from shell.session_service.infrastructure.session.session.persistence.sql.unit_of_work import (
    SqlAlchemySessionUnitOfWork,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker

_NOW_DT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_NOW = CreatedAt.from_datetime(_NOW_DT)
_OCCURRED = OccurredAt.from_datetime(_NOW_DT)


def _session(sess_id: str) -> Session:
    session = Session.open(
        id_=SessionId(sess_id),
        user_id=UserIdRef("user-1"),
        now=CreatedAt.from_datetime(_NOW_DT),
    )
    session.pull_events()
    return session


class TestSessionOutbox:
    async def test_close_writes_one_outbox_row(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemySessionUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            session = _session("outbox-session-close")
            session.close(now=_OCCURRED)
            await uow.save(SessionRepository, session)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("session_id") == "outbox-session-close"]
        assert len(rows) == 1, f"expected exactly 1 outbox row, got {len(rows)}"
        assert rows[0].payload.get("session_id") == "outbox-session-close"
        assert rows[0].integration_event_name == "SessionClosedIntegrationEvent"

    async def test_touch_writes_one_outbox_row(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemySessionUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            session = _session("outbox-session-touch")
            session.pull_events()
            session.touch(now=_OCCURRED)
            await uow.save(SessionRepository, session)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("session_id") == "outbox-session-touch"]
        assert len(rows) == 1
        assert rows[0].payload.get("session_id") == "outbox-session-touch"
        assert rows[0].integration_event_name == "SessionChangedIntegrationEvent"

    async def test_delete_writes_one_outbox_row(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemySessionUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            session = _session("outbox-session-delete")
            session.delete(now=_OCCURRED)
            await uow.save(SessionRepository, session)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("session_id") == "outbox-session-delete"]
        assert len(rows) == 1
        assert rows[0].payload.get("session_id") == "outbox-session-delete"
        assert rows[0].integration_event_name == "SessionDeletedIntegrationEvent"