"""OutboxRelayBase — cykl publikacji outbox → transport z izolacją poision.

Event i command relay dzielą ten sam cykl życia operacyjnego: claim pending
wierszy (``published_at IS NULL``), budowa kopert, dostawa do brokera,
rejestracja wyniku na wierszu. Dostawa lustrzaży cykl inbox processor
(``PENDING → PROCESSING → SENT / RETRY / DEAD_LETTER``) tak, że jeden
wiersz poison nigdy nie zablokuje partii za sobą.

Taksonomia błędów (dlaczego goły ``try/except`` per wiersz nie wystarczy):

- błędy budowania koperty są deterministyczne dla treści wiersza, więc wiersz
  trafia od razu do ``DEAD_LETTER`` (odtwarzalny po naprawie mappera);
- ``ConnectionError`` transportu oznacza, że broker jest niedostępny, więc
  runda przerywa: nieprzetworzone claimowane wiersze resetowane do ``PENDING``
  i błąd rzucany ponownie, by worker backing off zamiast spalać ``retry_count``
  na zdrowych wierszach podczas awarii;
- każdy inny błąd transportu (nack, unroutable, ambiguous timeout) przypisywany
  do wiersza: ``RETRY`` z wykładniczym backoffem, ``DEAD_LETTER`` po
  ``max_retries`` (at-least-once zachowane — timeoutowy publish mógł dotrzeć
  do brokera i zostać redelivered; konsument inbox deduplikuje na unikalnym
  ograniczeniu ``(source_service, event_id|command_id)``);
- breaker błędów ciągłych przerywa rundy kaskadowych kaskad.

Wszystkie znaczniki czasu używają zegara bazy danych, jak inbox claim service.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
import time
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import and_, func, or_, select, update

from shell.platform.application.error_sanitization import (
    sanitize_error_message,
)
from shell.platform.domain.value_objects.outbox_status import OutboxStatus
from shell.platform.infrastructure.messaging.delivery.outbox_batch_result import (
    OutboxBatchResult,
)

if TYPE_CHECKING:
    from sqlalchemy.engine import CursorResult
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

TRANSPORT_ERROR = "TRANSPORT_ERROR"
ENVELOPE_BUILD_ERROR = "ENVELOPE_BUILD_ERROR"


class OutboxRelayAbortedError(RuntimeError):
    """Runda relay przerwana przed wyczerpaniem claimowanej partii.

    Rzucony przy błędach fatalnych transportu (broker niedostępny) i przy
    wywołaniu breaker'a błędów ciągłych. Wyniki zapisane przed przerwaniem
    zostają zatwierdzone; nieprzetworzone claimowane wiersze resetowane do
    ``PENDING``. Worker polling traktuje to jak każdy błąd zadania i backs off.
    """


class OutboxRelayBase:
    """Publikuje oczekujące wiersze outbox z wynikami per-wiersz i bez blokowania głowy kolejki."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        transport: Any,
        batch_size: int = 100,
        max_retries: int = 3,
        retry_backoff_seconds: int = 30,
        max_retry_backoff_seconds: int = 3600,
        retry_jitter_seconds: float = 0.0,
        lease_duration_seconds: int = 60,
        consecutive_failure_limit: int = 20,
        worker_id: str | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._transport = transport
        self._batch_size = batch_size
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds
        self._max_retry_backoff_seconds = max_retry_backoff_seconds
        self._retry_jitter_seconds = retry_jitter_seconds
        self._lease_duration_seconds = lease_duration_seconds
        self._consecutive_failure_limit = max(consecutive_failure_limit, 1)
        from shell.platform.infrastructure.identity.uuid_technical_id_generator import (
            UuidTechnicalIdGenerator,
        )

        self._worker_id = worker_id or f"outbox-relay-{UuidTechnicalIdGenerator().new_id()}"

        engine = getattr(session_factory, "bind", None)
        dialect_name: str = engine.dialect.name if engine is not None else "unknown"
        self._skip_locked: bool = dialect_name not in ("sqlite",)

    @property
    def outbox_model(self) -> type[Any]:
        """Model ORM tabeli outbox dla danego kanału."""
        raise NotImplementedError

    @property
    def order_column(self) -> Any:
        """Kolumna porządkująca rekordy oczekujące (per kanał)."""
        raise NotImplementedError

    def _to_envelope(self, row: object) -> object:
        """Buduje kopertę delivery właściwą dla kanału z wiersza outbox."""
        raise NotImplementedError

    async def run_once(self) -> OutboxBatchResult:
        started = time.monotonic()
        claimed = await self._claim_batch()
        delivered = 0
        retried = 0
        dead_lettered = 0
        failed = 0
        consecutive_failures = 0
        for position, (row_id, retry_count, payload) in enumerate(claimed):
            try:
                envelope = self._to_envelope(payload)
            except Exception as exc:
                outcome = await self._dead_letter(
                    row_id,
                    error_code=ENVELOPE_BUILD_ERROR,
                    error_message=self._sanitize_error_message(exc),
                )
                if outcome == "dead_lettered":
                    dead_lettered += 1
                else:
                    failed += 1
                consecutive_failures += 1
                if consecutive_failures >= self._consecutive_failure_limit:
                    await self._reset_claimed([row_id for row_id, _, _ in claimed[position + 1 :]])
                    raise OutboxRelayAbortedError(
                        f"outbox relay aborted (consecutive-failure breaker tripped "
                        f"at {consecutive_failures}): delivered={delivered} "
                        f"retried={retried} dead_lettered={dead_lettered}"
                    ) from None
                continue
            try:
                await self._transport.deliver(envelope)
            except asyncio.CancelledError:
                await self._reset_claimed([row_id for row_id, _, _ in claimed[position:]])
                raise
            except ConnectionError as exc:
                await self._reset_claimed([row_id for row_id, _, _ in claimed[position:]])
                raise OutboxRelayAbortedError(
                    f"outbox relay aborted (broker unreachable): "
                    f"delivered={delivered} retried={retried} "
                    f"dead_lettered={dead_lettered}"
                ) from exc
            except Exception as exc:
                outcome = await self._schedule_failure(
                    row_id,
                    error_code=TRANSPORT_ERROR,
                    error_message=self._sanitize_error_message(exc),
                    current_retry_count=retry_count,
                )
            else:
                outcome = "sent" if await self._acknowledge(row_id) else "failed"
            if outcome == "sent":
                delivered += 1
                consecutive_failures = 0
            elif outcome == "retried":
                retried += 1
                consecutive_failures += 1
            elif outcome == "dead_lettered":
                dead_lettered += 1
                consecutive_failures += 1
            else:
                failed += 1
                consecutive_failures += 1
            if consecutive_failures >= self._consecutive_failure_limit:
                await self._reset_claimed([row_id for row_id, _, _ in claimed[position + 1 :]])
                raise OutboxRelayAbortedError(
                    f"outbox relay aborted (consecutive-failure breaker tripped "
                    f"at {consecutive_failures}): delivered={delivered} "
                    f"retried={retried} dead_lettered={dead_lettered}"
                )
        return OutboxBatchResult(
            claimed_count=len(claimed),
            processed_count=delivered,
            retried_count=retried,
            dead_lettered_count=dead_lettered,
            failed_count=failed,
            duration_ms=int((time.monotonic() - started) * 1000),
        )

    async def _claim_batch(self) -> list[tuple[str, int, SimpleNamespace]]:
        model = self.outbox_model
        async with self._session_factory() as session:
            now = await self._database_now(session)
            stmt = (
                select(model)
                .where(
                    model.published_at.is_(None),
                    or_(
                        and_(
                            model.status.in_(
                                [OutboxStatus.PENDING.value, OutboxStatus.RETRY.value]
                            ),
                            model.next_attempt_at <= now,
                        ),
                        and_(
                            model.status == OutboxStatus.PROCESSING.value,
                            or_(
                                model.lease_until.is_(None),
                                model.lease_until < now,
                            ),
                        ),
                    ),
                )
                .order_by(self.order_column)
                .limit(self._batch_size)
            )
            if self._skip_locked:
                stmt = stmt.with_for_update(skip_locked=True)

            rows = (await session.execute(stmt)).scalars().all()

            claimed: list[tuple[str, int, SimpleNamespace]] = []
            for row in rows:
                row.status = OutboxStatus.PROCESSING.value
                row.claimed_by = self._worker_id
                row.lease_until = now + timedelta(seconds=self._lease_duration_seconds)
                payload = SimpleNamespace(
                    **{column.key: getattr(row, column.key) for column in row.__table__.columns}
                )
                claimed.append((row.id, row.retry_count, payload))

            await session.commit()
            return claimed

    async def _acknowledge(self, row_id: str) -> bool:
        model = self.outbox_model
        async with self._session_factory() as session:
            now = await self._database_now(session)
            result = await session.execute(
                update(model)
                .where(
                    model.id == row_id,
                    model.status == OutboxStatus.PROCESSING.value,
                    model.claimed_by == self._worker_id,
                )
                .values(
                    status=OutboxStatus.SENT.value,
                    published_at=now,
                    lease_until=None,
                    claimed_by=None,
                    retry_count=0,
                    last_attempted_at=None,
                    error_code=None,
                    error_message=None,
                )
            )
            await session.commit()
            return cast("CursorResult[object]", result).rowcount == 1

    async def _schedule_failure(
        self,
        row_id: str,
        *,
        error_code: str,
        error_message: str,
        current_retry_count: int,
        immediate_dead_letter: bool = False,
    ) -> str:
        next_retry_count = current_retry_count + 1
        dead_letter = immediate_dead_letter or next_retry_count >= self._max_retries

        async with self._session_factory() as session:
            now = await self._database_now(session)
            values: dict[str, object] = {
                "retry_count": next_retry_count,
                "last_attempted_at": now,
                "lease_until": None,
                "claimed_by": None,
                "error_code": error_code,
                "error_message": error_message,
            }
            if dead_letter:
                values["status"] = OutboxStatus.DEAD_LETTER.value
                values["failed_at"] = now
                logger.critical(
                    "%s exceeded max_retries=%s — DLQ",
                    row_id,
                    self._max_retries,
                )
            else:
                values["status"] = OutboxStatus.RETRY.value
                values["next_attempt_at"] = now + self._backoff(next_retry_count)

            result = await session.execute(
                update(self.outbox_model)
                .where(
                    self.outbox_model.id == row_id,
                    self.outbox_model.status == OutboxStatus.PROCESSING.value,
                    self.outbox_model.claimed_by == self._worker_id,
                )
                .values(**values)
            )
            await session.commit()

        if cast("CursorResult[object]", result).rowcount == 0:
            return "failed"
        return "dead_lettered" if dead_letter else "retried"

    async def _dead_letter(self, row_id: str, *, error_code: str, error_message: str) -> str:
        return await self._schedule_failure(
            row_id,
            error_code=error_code,
            error_message=error_message,
            current_retry_count=0,
            immediate_dead_letter=True,
        )

    async def _reset_claimed(self, row_ids: list[str]) -> None:
        if not row_ids:
            return
        model = self.outbox_model
        async with self._session_factory() as session:
            await session.execute(
                update(model)
                .where(
                    model.id.in_(row_ids),
                    model.status == OutboxStatus.PROCESSING.value,
                    model.claimed_by == self._worker_id,
                )
                .values(lease_until=None, claimed_by=None, status=OutboxStatus.PENDING.value)
            )
            await session.commit()

    def _backoff(self, retry_count: int) -> timedelta:
        delay = min(
            self._max_retry_backoff_seconds,
            self._retry_backoff_seconds * (2 ** max(retry_count - 1, 0)),
        )
        jitter = secrets.SystemRandom().uniform(0.0, self._retry_jitter_seconds)
        return timedelta(seconds=delay + jitter)

    @staticmethod
    def _sanitize_error_message(exc: BaseException) -> str:
        return sanitize_error_message(exc)

    async def _database_now(self, session: AsyncSession) -> datetime:
        raw = (await session.execute(select(func.current_timestamp()))).scalar_one()
        if isinstance(raw, str):
            raw = datetime.fromisoformat(raw)
        if raw.tzinfo is None:
            raw = raw.replace(tzinfo=UTC)
        return raw