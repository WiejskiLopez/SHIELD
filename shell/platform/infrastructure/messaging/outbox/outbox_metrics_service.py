"""OutboxMetricsService — pending outbox backlog metric for delivery monitoring."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

from shell.platform.domain.value_objects.outbox_status import OutboxStatus

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from shell.platform.observability.application.ports.metrics import MetricsBackend

logger = logging.getLogger(__name__)


class OutboxMetricsService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        outbox_model: type[Any],
        backend: MetricsBackend | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._outbox_model = outbox_model
        self._backend = backend

    async def snapshot(self) -> int:
        """Return the number of outbox rows waiting for publication.

        Terminally failed (``DEAD_LETTER``) rows are excluded from the pending
        backlog and reported through the dead-letter gauge instead, so a
        poisoned queue does not look like ordinary lag.
        """
        async with self._session_factory() as session:
            pending = (
                await session.execute(
                    select(func.count())
                    .select_from(self._outbox_model)
                    .where(
                        self._outbox_model.published_at.is_(None),
                        self._outbox_model.status != OutboxStatus.DEAD_LETTER.value,
                    )
                )
            ).scalar_one()
            dead_lettered = (
                await session.execute(
                    select(func.count())
                    .select_from(self._outbox_model)
                    .where(self._outbox_model.status == OutboxStatus.DEAD_LETTER.value)
                )
            ).scalar_one()
        self._emit(int(pending), int(dead_lettered))
        return int(pending)

    def _emit(self, pending: int, dead_lettered: int) -> None:
        if self._backend is None:
            return
        try:
            self._backend.record_outbox_backlog(pending=pending)
            self._backend.record_outbox_dead_lettered(dead_lettered=dead_lettered)
        except Exception:
            logger.exception("metrics backend failed to record outbox backlog snapshot")
