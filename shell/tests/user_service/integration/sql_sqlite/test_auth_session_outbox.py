"""Outbox e2e: mutacja FSM AuthSession przez save() musi zostawić dokładnie 1 wiersz w event_outbox."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select

from shell.platform.domain.value_objects.created_at import CreatedAt
from shell.platform.domain.value_objects.hash import Hash
from shell.platform.domain.value_objects.occurred_at import OccurredAt
from shell.user_service.domain.user.aggregates.auth_session.auth_session import AuthSession
from shell.user_service.domain.user.aggregates.auth_session.repositories.auth_session_repository import (
    AuthSessionRepository,
)
from shell.user_service.domain.user.aggregates.auth_session.value_objects.auth_session_id import (
    AuthSessionId,
)
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
_TTL = timedelta(hours=1)


def _auth_session(auth_id: str) -> AuthSession:
    auth = AuthSession.create(
        id_=AuthSessionId(auth_id),
        user_id=UserId("user-1"),
        token_hash=Hash("a" * 64),
        session_ttl=timedelta(hours=1),
        now=CreatedAt.from_datetime(_NOW_DT),
    )
    auth.pull_events()
    return auth


class TestAuthSessionOutbox:
    async def test_renew_token_writes_one_outbox_row(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyUserUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            auth = _auth_session("outbox-auth-renew")
            auth.renew_token(token_hash=Hash("b" * 64), now=_OCCURRED)
            await uow.save(AuthSessionRepository, auth)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("auth_session_id") == "outbox-auth-renew"]
        assert len(rows) == 1, f"expected exactly 1 outbox row, got {len(rows)}"
        assert rows[0].payload.get("auth_session_id") == "outbox-auth-renew"
        assert rows[0].integration_event_name == "AuthSessionChangedIntegrationEvent"

    async def test_touch_writes_one_outbox_row(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyUserUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            auth = _auth_session("outbox-auth-touch")
            auth.pull_events()
            auth.touch(now=_OCCURRED)
            await uow.save(AuthSessionRepository, auth)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("auth_session_id") == "outbox-auth-touch"]
        assert len(rows) == 1
        assert rows[0].payload.get("auth_session_id") == "outbox-auth-touch"
        assert rows[0].integration_event_name == "AuthSessionChangedIntegrationEvent"

    async def test_delete_writes_one_outbox_row(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyUserUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            auth = _auth_session("outbox-auth-delete")
            auth.delete(now=_OCCURRED)
            await uow.save(AuthSessionRepository, auth)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("auth_session_id") == "outbox-auth-delete"]
        assert len(rows) == 1
        assert rows[0].payload.get("auth_session_id") == "outbox-auth-delete"
        assert rows[0].integration_event_name == "AuthSessionDeletedIntegrationEvent"

    async def test_revoke_writes_one_outbox_row(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyUserUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            auth = _auth_session("outbox-auth-revoke")
            auth.pull_events()
            auth.revoke(now=_OCCURRED)
            await uow.save(AuthSessionRepository, auth)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("auth_session_id") == "outbox-auth-revoke"]
        assert len(rows) == 1
        assert rows[0].payload.get("auth_session_id") == "outbox-auth-revoke"
        assert rows[0].integration_event_name == "AuthSessionRevokedIntegrationEvent"