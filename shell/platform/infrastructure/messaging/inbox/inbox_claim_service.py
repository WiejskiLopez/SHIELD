"""InboxClaimService — atomowo claimuje rekordy dostawy inbox z lease'em.

Zastępuje długie zamki bazy starszego procesora krótką transakcję claim:
worker wybiera rekordy pending/retry, oznacza je ``PROCESSING``,
ustawia ``claimed_by`` i ``lease_until``, i commituje. Rekordy
opuszczone przez martwego workera odzyskiwane po wygaśnięciu lease'u.

Wszystkie czasy używają zegara bazy danych (``CURRENT_TIMESTAMP``) więc
wygaśnięcie lease'u spójne między workerami niezależnie od dryfu
zegarów maszyn aplikacyjnych.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Protocol, cast

from sqlalchemy import and_, func, or_, select, update

from shell.platform.domain.value_objects.inbox_status import InboxStatus

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy.orm import Mapped


class InboxStateModel(Protocol):
    """Kolumny, które musi udostępniać model inbox claimowalny (dostarczane przez ``InboxStateMixin``)."""

    id: Mapped[str]
    status: Mapped[str]
    next_attempt_at: Mapped[datetime]
    lease_until: Mapped[datetime | None]
    claimed_by: Mapped[str | None]
    received_at: Mapped[datetime]
    processed_at: Mapped[datetime | None]
    failed_at: Mapped[datetime | None]
    last_attempted_at: Mapped[datetime | None]
    retry_count: Mapped[int]
    error: Mapped[str | None]
    error_code: Mapped[str | None]
    error_message: Mapped[str | None]
    schema_version: Mapped[int]


class _ClaimableRow(Protocol):
    """Runtime instance shape used while mutating claimed rows."""

    status: str
    lease_until: datetime | None
    claimed_by: str | None


class InboxClaimService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        inbox_model: type[InboxStateModel],
        worker_id: str,
        lease_duration_seconds: int,
        batch_size: int = 100,
    ) -> None:
        self._session_factory = session_factory
        self._inbox_model = inbox_model
        self._worker_id = worker_id
        self._lease_duration_seconds = lease_duration_seconds
        self._batch_size = batch_size

        engine = getattr(session_factory, "bind", None)
        dialect_name: str = engine.dialect.name if engine is not None else "unknown"
        self._dialect_name = dialect_name
        self._skip_locked: bool = dialect_name not in ("sqlite",)

    async def claim_batch(self, limit: int | None = None) -> list[object]:
        """Zaclaimuj do ``batch_size`` rekordów w jednej krótkiej transakcji.

        ``limit`` nadpisuje skonfigurowany batch size dla tego wywołania (używane
        przez procesor do wymuszenia partii jednoelementowej gdy heartbeat wyłączony).

        Zwraca zclaimowane rekordy (status ``PROCESSING``, ``claimed_by`` i
        ``lease_until`` już zapisane i skomitowane). Callery własność
        zwróconych wierszy i są oczekiwane do przetworzenia i ackowania.
        """
        batch_size = limit if limit is not None else self._batch_size
        async with self._session_factory() as session:
            now = await self._database_now(session)

            stmt = (
                select(self._inbox_model)
                .where(
                    or_(
                        and_(
                            self._inbox_model.status.in_(
                                [InboxStatus.PENDING.value, InboxStatus.RETRY.value]
                            ),
                            self._inbox_model.next_attempt_at <= now,
                        ),
                        and_(
                            self._inbox_model.status == InboxStatus.PROCESSING.value,
                            or_(
                                self._inbox_model.lease_until.is_(None),
                                self._inbox_model.lease_until < now,
                            ),
                        ),
                    )
                )
                .order_by(self._inbox_model.received_at)
                .limit(batch_size)
            )
            if self._skip_locked:
                stmt = stmt.with_for_update(skip_locked=True)

            if self._dialect_name == "sqlite":
                claim_ids = stmt.with_only_columns(self._inbox_model.id)
                claim_stmt = (
                    update(self._inbox_model)
                    .where(self._inbox_model.id.in_(claim_ids))
                    .values(
                        status=InboxStatus.PROCESSING.value,
                        claimed_by=self._worker_id,
                        lease_until=now + timedelta(seconds=self._lease_duration_seconds),
                    )
                    .returning(self._inbox_model)
                )
                rows = (await session.execute(claim_stmt)).scalars().all()
                await session.commit()
                return list(rows)

            rows = (await session.execute(stmt)).scalars().all()

            claimed: list[object] = []
            for row in rows:
                mutable = cast("_ClaimableRow", row)
                mutable.status = InboxStatus.PROCESSING.value
                mutable.claimed_by = self._worker_id
                mutable.lease_until = now + timedelta(seconds=self._lease_duration_seconds)
                claimed.append(row)

            await session.commit()
            return claimed

    async def _database_now(self, session: AsyncSession) -> datetime:
        raw = (await session.execute(select(func.current_timestamp()))).scalar_one()
        if isinstance(raw, str):
            raw = datetime.fromisoformat(raw)
        if raw.tzinfo is None:
            raw = raw.replace(tzinfo=UTC)
        return raw