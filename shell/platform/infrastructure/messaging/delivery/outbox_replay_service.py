"""OutboxReplayService — bezpieczne administracyjne odtwarzanie rekordów dostawy outbox.

Odtwarzanie resetuje dostawę z powrotem do ``PENDING``, aby relay pobrał ją ponownie.
Reset jest **wyłączny względem aktywnych relayów**: rekord aktualnie ``PROCESSING`` z
niewygasłym lease'em nigdy nie jest dotykany, więc odtwarzanie nie może wyścigić
z aktywnym relayem.

Odtwarzanie zachowuje oryginalny payload i adresowanie — czyści tylko pola
operacyjnego cyklu życia (status/retry/error/lease/published marker), ale nigdy
payload, typ ani id korelacji/korelacji. Każde odtwarzanie jest rejestrowane
z operatorem i przyczyną dla audytu.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import func, or_, select, update

from shell.platform.domain.value_objects.outbox_status import OutboxStatus

if TYPE_CHECKING:
    from sqlalchemy.engine import CursorResult
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy.sql.elements import ColumnElement

logger = logging.getLogger(__name__)


class OutboxReplayService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        outbox_model: type[Any],
    ) -> None:
        self._session_factory = session_factory
        self._outbox_model = outbox_model

    async def replay_by_id(
        self,
        record_id: str,
        *,
        operator: str,
        reason: str,
    ) -> bool:
        """Zresetuj pojedynczą dostawę do ``PENDING``.

        Zwraca ``True`` gdy rekord został odtworzony. Rekord aktywnie trzymany przez
        relay (``PROCESSING`` z niewygasłym lease'em) jest pomijany.
        """
        async with self._session_factory() as session:
            now = await self._database_now(session)
            result = await session.execute(
                update(self._outbox_model)
                .where(
                    self._outbox_model.id == record_id,
                    self._is_replayable(self._outbox_model),
                )
                .values(**self._reset_values(now))
            )
            await session.commit()

        replayed = cast("CursorResult[object]", result).rowcount > 0
        if replayed:
            logger.info(
                "outbox.replay id=%s operator=%s reason=%s",
                record_id,
                operator,
                reason,
            )
        return replayed

    async def replay_sent(self, *, operator: str, reason: str) -> int:
        """Zresetuj każdy rekord ``SENT`` z powrotem do ``PENDING`` (ponowna dostawa).

        Zwraca liczbę odtworzonych rekordów.
        """
        return await self._replay_many(
            status_filter=OutboxStatus.SENT.value,
            operator=operator,
            reason=reason,
        )

    async def replay_dead_lettered(self, *, operator: str, reason: str) -> int:
        """Zresetuj każdy rekord ``DEAD_LETTER`` z powrotem do ``PENDING``.

        Zwraca liczbę odtworzonych rekordów.
        """
        return await self._replay_many(
            status_filter=OutboxStatus.DEAD_LETTER.value,
            operator=operator,
            reason=reason,
        )

    async def _replay_many(
        self,
        *,
        status_filter: str,
        operator: str,
        reason: str,
    ) -> int:
        async with self._session_factory() as session:
            now = await self._database_now(session)
            stmt = (
                update(self._outbox_model)
                .where(
                    self._outbox_model.status == status_filter,
                    self._is_replayable(self._outbox_model),
                )
                .values(**self._reset_values(now))
            )
            result = await session.execute(stmt)
            await session.commit()

        count = cast("CursorResult[object]", result).rowcount
        logger.info(
            "outbox.replay batch status=%s count=%s operator=%s reason=%s",
            status_filter,
            count,
            operator,
            reason,
        )
        return count

    def _is_replayable(self, model: type[Any]) -> ColumnElement[bool]:
        return or_(
            model.status != OutboxStatus.PROCESSING.value,
            model.lease_until < func.current_timestamp(),
        )

    def _reset_values(self, now: datetime) -> dict[str, object]:
        return {
            "status": OutboxStatus.PENDING.value,
            "published_at": None,
            "next_attempt_at": now,
            "retry_count": 0,
            "last_attempted_at": None,
            "lease_until": None,
            "claimed_by": None,
            "failed_at": None,
            "error_code": None,
            "error_message": None,
        }

    async def _database_now(self, session: AsyncSession) -> datetime:
        raw = (await session.execute(select(func.current_timestamp()))).scalar_one()
        if isinstance(raw, str):
            raw = datetime.fromisoformat(raw)
        if raw.tzinfo is None:
            raw = raw.replace(tzinfo=UTC)
        return raw