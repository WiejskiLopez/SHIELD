"""Outbox e2e: mutacja FSM User przez save() musi zostawić dokładnie 1 wiersz w event_outbox."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from shell.platform.domain.value_objects.created_at import CreatedAt
from shell.platform.domain.value_objects.occurred_at import OccurredAt
from shell.user_service.domain.user.aggregates.user.repositories.user_repository import (
    UserRepository,
)
from shell.user_service.domain.user.aggregates.user.user import User
from shell.user_service.domain.user.value_objects.user_email import UserEmail
from shell.user_service.domain.user.value_objects.user_id import UserId
from shell.user_service.infrastructure.user.persistence.sql.models.base import (
    PERSISTENCE_DELIVERY_MODELS,
    OutboxEventModel,
)
from shell.user_service.infrastructure.user.user.persistence.sql.unit_of_work import (
    SqlAlchemyUserUnitOfWork,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker

_NOW_DT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_NOW = CreatedAt.from_datetime(_NOW_DT)
_OCCURRED = OccurredAt.from_datetime(_NOW_DT)


def _user(user_id: str, email: str) -> User:
    user = User.create(
        id=UserId(user_id),
        email=UserEmail(email),
        now=CreatedAt.from_datetime(_NOW_DT),
    )
    user.pull_events()
    return user


class TestUserOutbox:
    async def test_disable_writes_one_outbox_row(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyUserUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            user = _user("outbox-user-disable", "disable@example.com")
            user.pull_events()
            user.disable(now=OccurredAt.from_datetime(_NOW_DT))
            await uow.save(UserRepository, user)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("user_id") == "outbox-user-disable"]
        # disable emits 2 events: ChangedEvent + DisabledEvent
        assert len(rows) == 2, f"expected exactly 2 outbox rows for disable, got {len(rows)}"
        event_names = {row.integration_event_name for row in rows}
        assert event_names == {
            "UserChangedIntegrationEvent",
            "UserDisabledIntegrationEvent",
        }

    async def test_enable_writes_one_outbox_row(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyUserUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            user = _user("outbox-user-enable", "enable@example.com")
            user.pull_events()
            user.disable(now=OccurredAt.from_datetime(_NOW_DT))
            user.pull_events()
            user.enable(now=OccurredAt.from_datetime(_NOW_DT))
            await uow.save(UserRepository, user)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("user_id") == "outbox-user-enable"]
        # enable emits 2 events: ChangedEvent + EnabledEvent
        assert len(rows) == 2
        event_names = {row.integration_event_name for row in rows}
        assert event_names == {
            "UserChangedIntegrationEvent",
            "UserEnabledIntegrationEvent",
        }