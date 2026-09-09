"""DeliveryRetentionService — bounded retention/cleanup for delivery tables.

Policies:

- DLQ inbox rows older than ``dead_letter_retention_days`` are purged — the
  payload, type and error metadata are no longer operationally actionable.

Deduplikacja delivery jest realizowana constraintami na tabelach inbox
(``UNIQUE(source_service, event_id|command_id)``) oraz statusem ``PROCESSED``,
więc nie wymaga osobnej tabeli retencji.

Retention windows are configurable. Purges run in a single transaction so a
crash leaves the table consistent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

from sqlalchemy import delete, func, select

from shell.platform.domain.value_objects.inbox_status import InboxStatus
from shell.platform.domain.value_objects.outbox_status import OutboxStatus

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any

    from sqlalchemy.engine import CursorResult
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy.sql.dml import Delete
    from sqlalchemy.sql.elements import ColumnElement

    from shell.platform.infrastructure.messaging.inbox.inbox_claim_service import (
        InboxStateModel,
    )


@dataclass(frozen=True, slots=True)
class RetentionReport:
    purged_dead_letter: int = 0
    kept_dead_letter: int = 0
    purged_outbox_dead_letter: int = 0
    kept_outbox_dead_letter: int = 0
    detail: dict[str, object] = field(default_factory=dict)


class DeliveryRetentionService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        inbox_model: type[InboxStateModel],
        *,
        outbox_models: Sequence[type[Any]] = (),
        dead_letter_retention_days: int = 90,
        now: datetime | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._inbox_model = inbox_model
        self._outbox_models = tuple(outbox_models)
        self._dead_letter_cutoff = (now or datetime.now(tz=UTC)) - timedelta(
            days=dead_letter_retention_days
        )

    async def purge_expired(self) -> RetentionReport:
        async with self._session_factory() as session:
            kept_dead_letter = await self._count(
                session,
                self._inbox_model,
                self._inbox_model.status == InboxStatus.DEAD_LETTER.value,
            )
            purged_dead_letter = await self._delete(
                session,
                delete(self._inbox_model).where(
                    self._inbox_model.status == InboxStatus.DEAD_LETTER.value,
                    self._inbox_model.failed_at < self._dead_letter_cutoff,
                ),
            )
            kept_outbox_dead_letter = 0
            purged_outbox_dead_letter = 0
            for outbox_model in self._outbox_models:
                kept_outbox_dead_letter += await self._count(
                    session,
                    outbox_model,
                    outbox_model.status == OutboxStatus.DEAD_LETTER.value,
                )
                purged_outbox_dead_letter += await self._delete(
                    session,
                    delete(outbox_model).where(
                        outbox_model.status == OutboxStatus.DEAD_LETTER.value,
                        outbox_model.failed_at < self._dead_letter_cutoff,
                    ),
                )
            await session.commit()

        return RetentionReport(
            purged_dead_letter=purged_dead_letter,
            kept_dead_letter=kept_dead_letter,
            purged_outbox_dead_letter=purged_outbox_dead_letter,
            kept_outbox_dead_letter=kept_outbox_dead_letter,
            detail={"dead_letter_cutoff": self._dead_letter_cutoff.isoformat()},
        )

    async def _count(
        self,
        session: AsyncSession,
        model: type[Any],
        condition: ColumnElement[bool],
    ) -> int:
        result = await session.execute(select(func.count()).select_from(model).where(condition))
        return int(result.scalar_one())

    async def _delete(self, session: AsyncSession, statement: Delete) -> int:
        result = await session.execute(statement)
        return int(cast("CursorResult[object]", result).rowcount or 0)
