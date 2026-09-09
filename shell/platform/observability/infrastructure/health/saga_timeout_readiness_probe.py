"""SagaTimeoutReadinessProbe — readiness backlogu timeoutów sagi.

Serwis jest gotowy, gdy tabela `saga_timeout` nie ma zaległych wierszy powyżej
progu: dojrzałe PENDING albo CLAIMED z wygasłym lease. Nawał timeoutów nie może
wyglądać jak „usługa zdrowa". Nigdy nie rzuca — raportuje diagnostykę na 503.

Słownik statusów (`pending`/`claimed`) pochodzi z saga-orchestration
(`TimeoutStatus`); model wiersza dostarcza właściciel sagi strukturalnie.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from sqlalchemy import and_, func, or_, select, text

from shell.platform.observability.application.ports.readiness import (
    ReadinessProbe,
    ReadinessReport,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy.orm import Mapped


class SagaTimeoutReadModel(Protocol):
    """Kształt odczytu wiersza saga_timeout (dostarcza właściciel sagi)."""

    status: Mapped[str]
    due_at: Mapped[datetime]
    lease_until: Mapped[datetime | None]


class SagaTimeoutReadinessProbe(ReadinessProbe):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        timeout_model: type[SagaTimeoutReadModel],
        max_backlog: int = 100,
    ) -> None:
        self._session_factory = session_factory
        self._timeout_model = timeout_model
        self._max_backlog = max_backlog

    async def check(self) -> ReadinessReport:
        checks: dict[str, object] = {}
        try:
            async with self._session_factory() as session:
                checks["database"] = await self._check_database(session)
                checks["migrations"] = await self._check_migrations(session)
                checks["backlog"] = await self._check_backlog(session)
        except Exception as exc:
            checks["database"] = f"error: {type(exc).__name__}: {exc}"
            checks["migrations"] = "not checked"
            checks["backlog"] = "not checked"

        ready = all(isinstance(value, bool) and value is True for value in checks.values())
        return ReadinessReport(ready=ready, checks=checks)

    async def _check_database(self, session: AsyncSession) -> bool:
        await session.execute(text("SELECT 1"))
        return True

    async def _check_migrations(self, session: AsyncSession) -> bool:
        try:
            await session.execute(select(func.count()).select_from(self._timeout_model).limit(1))
            return True
        except Exception:
            return False

    async def _check_backlog(self, session: AsyncSession) -> bool:
        now = datetime.now(tz=UTC)
        result = await session.execute(
            select(func.count())
            .select_from(self._timeout_model)
            .where(
                or_(
                    and_(
                        self._timeout_model.status == "pending",
                        self._timeout_model.due_at <= now,
                    ),
                    and_(
                        self._timeout_model.status == "claimed",
                        self._timeout_model.lease_until < now,
                    ),
                )
            )
        )
        return int(result.scalar_one()) <= self._max_backlog
