from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import and_, func, or_, select

from saga_orchestration.domain.timeout_status import TimeoutStatus

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession

    from saga_orchestration.infrastructure.sqlalchemy.saga_models import SagaModels


async def count_overdue_timeouts(session: AsyncSession, models: SagaModels, now: datetime) -> int:
    """Zaległe timeouty: PENDING po due_at + CLAIMED z wygasłym lease. Dla readiness probe."""
    result = await session.execute(
        select(func.count())
        .select_from(models.timeout)
        .where(
            or_(
                and_(
                    models.timeout.status == TimeoutStatus.PENDING.value,
                    models.timeout.due_at <= now,
                ),
                and_(
                    models.timeout.status == TimeoutStatus.CLAIMED.value,
                    models.timeout.lease_until < now,
                ),
            )
        )
    )
    return int(result.scalar_one())
