from __future__ import annotations

from typing import TYPE_CHECKING

from saga_orchestration.infrastructure.sqlalchemy.sql_saga_repository import (
    SqlSagaRepository,
)
from saga_orchestration.infrastructure.sqlalchemy.sql_saga_timeout_repository import (
    SqlSagaTimeoutRepository,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from types import TracebackType

    from sqlalchemy.ext.asyncio import AsyncSession

    from saga_orchestration.domain.ports.outbox_writer import CommandOutboxWriter, OutboxCommandRow
    from saga_orchestration.domain.ports.saga_repository import SagaRepository
    from saga_orchestration.domain.ports.saga_timeout_repository import SagaTimeoutRepository
    from saga_orchestration.domain.step import StepRegistry
    from saga_orchestration.infrastructure.sqlalchemy.saga_models import SagaModels


class SqlSagaUnitOfWork:
    """Sesja należy do SERWISU. UoW jej nie otwiera; zamyka tylko własną."""

    def __init__(
        self,
        session: AsyncSession,
        models: SagaModels,
        outbox_writer: CommandOutboxWriter,
        registries: Mapping[str, StepRegistry],
        *,
        owns_session: bool,
    ) -> None:
        self._session = session
        self._sagas = SqlSagaRepository(session, models, registries)
        self._timeouts = SqlSagaTimeoutRepository(session, models)
        self._outbox_writer = outbox_writer
        self._owns_session = owns_session
        self._settled = False

    async def __aenter__(self) -> SqlSagaUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
            return
        if not self._settled:
            await self.commit()

    @property
    def sagas(self) -> SagaRepository:
        return self._sagas

    @property
    def timeouts(self) -> SagaTimeoutRepository:
        return self._timeouts

    def append_command(self, row: OutboxCommandRow) -> None:
        self._outbox_writer.append(row)

    async def commit(self) -> None:
        await self._session.flush()
        await self._session.commit()
        self._settled = True

    async def rollback(self) -> None:
        await self._session.rollback()
        self._settled = True

    async def close(self) -> None:
        if self._owns_session:
            await self._session.close()
