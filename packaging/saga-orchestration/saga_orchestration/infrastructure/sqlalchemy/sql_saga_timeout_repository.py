from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import and_, or_, select, update

from saga_orchestration.domain.errors import SagaGuardError
from saga_orchestration.domain.saga_id import SagaId
from saga_orchestration.domain.saga_key import SagaKey
from saga_orchestration.domain.saga_timeout import ClaimedTimeout, SagaTimeout
from saga_orchestration.domain.step_name import StepName
from saga_orchestration.domain.timeout_id import TimeoutId
from saga_orchestration.domain.timeout_kind import TimeoutKind
from saga_orchestration.domain.timeout_status import TimeoutStatus
from saga_orchestration.infrastructure.sqlalchemy.saga_models import affected_rows

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession

    from saga_orchestration.infrastructure.sqlalchemy.saga_models import (
        SagaModels,
        SagaTimeoutRow,
    )


class SqlSagaTimeoutRepository:
    """Timeouty w tej samej sesji co saga. Claim: UPDATE + odczyt własnych."""

    def __init__(self, session: AsyncSession, models: SagaModels) -> None:
        self._session = session
        self._models = models

    async def schedule(self, entry: SagaTimeout) -> None:
        self._session.add(
            self._models.timeout(
                id=entry.timeout_id.value,
                saga_id=entry.saga_id.value,
                saga_type=entry.key.saga_type,
                saga_key=entry.key.business_key,
                step=entry.step.value,
                attempt=entry.attempt,
                kind=entry.kind.value,
                due_at=entry.due_at,
                status=TimeoutStatus.PENDING.value,
                owner=None,
                lease_until=None,
                correlation_id=entry.correlation_id,
                causation_id=entry.causation_id,
            )
        )
        await self._session.flush()

    async def cancel_for_step(self, saga_id: SagaId, step: StepName) -> int:
        result = await self._session.execute(
            update(self._models.timeout)
            .where(
                self._models.timeout.saga_id == saga_id.value,
                self._models.timeout.step == step.value,
                self._models.timeout.status == TimeoutStatus.PENDING.value,
            )
            .values(status=TimeoutStatus.CANCELLED.value)
        )
        return affected_rows(result)

    async def cancel_for_saga(self, saga_id: SagaId) -> int:
        result = await self._session.execute(
            update(self._models.timeout)
            .where(
                self._models.timeout.saga_id == saga_id.value,
                self._models.timeout.status == TimeoutStatus.PENDING.value,
            )
            .values(status=TimeoutStatus.CANCELLED.value)
        )
        return affected_rows(result)

    async def claim_due(
        self, *, owner: str, now: datetime, lease_until: datetime, limit: int
    ) -> tuple[ClaimedTimeout, ...]:
        await self._session.execute(
            update(self._models.timeout)
            .where(
                or_(
                    and_(
                        self._models.timeout.status == TimeoutStatus.PENDING.value,
                        self._models.timeout.due_at <= now,
                        or_(
                            self._models.timeout.owner.is_(None),
                            self._models.timeout.lease_until < now,
                        ),
                    ),
                    and_(
                        self._models.timeout.status == TimeoutStatus.CLAIMED.value,
                        self._models.timeout.lease_until < now,
                    ),
                )
            )
            .values(
                status=TimeoutStatus.CLAIMED.value,
                owner=owner,
                lease_until=lease_until,
            )
        )
        rows = (
            await self._session.execute(
                select(self._models.timeout)
                .where(
                    self._models.timeout.owner == owner,
                    self._models.timeout.status == TimeoutStatus.CLAIMED.value,
                )
                .order_by(self._models.timeout.due_at)
                .limit(limit)
            )
        ).scalars()
        return tuple(self._to_claimed(row) for row in rows)

    async def mark_done(self, timeout_id: TimeoutId) -> None:
        result = await self._session.execute(
            update(self._models.timeout)
            .where(
                self._models.timeout.id == timeout_id.value,
                self._models.timeout.status == TimeoutStatus.CLAIMED.value,
            )
            .values(status=TimeoutStatus.DONE.value)
        )
        if affected_rows(result) != 1:
            raise SagaGuardError(f"timeout {timeout_id.value} nie jest CLAIMED")

    def _to_claimed(self, row: SagaTimeoutRow) -> ClaimedTimeout:
        try:
            kind = TimeoutKind(row.kind)
        except ValueError as exc:
            raise SagaGuardError(f"nieznany kind timeoutu w bazie: {row.kind!r}") from exc
        return ClaimedTimeout(
            timeout_id=TimeoutId(row.id),
            saga_id=SagaId(row.saga_id),
            key=SagaKey(saga_type=row.saga_type, business_key=row.saga_key),
            step=StepName(row.step),
            attempt=int(row.attempt),
            kind=kind,
            correlation_id=row.correlation_id,
            causation_id=row.causation_id,
        )
