from __future__ import annotations

from typing import TYPE_CHECKING

from saga_orchestration.domain.errors import SagaGuardError
from saga_orchestration.domain.saga_timeout import ClaimedTimeout, SagaTimeout
from saga_orchestration.domain.timeout_status import TimeoutStatus
from saga_orchestration.infrastructure.in_memory.in_memory_store import (
    SagaMemoryStore,
    StoredTimeout,
)

if TYPE_CHECKING:
    from datetime import datetime

    from saga_orchestration.domain.saga_id import SagaId
    from saga_orchestration.domain.step_name import StepName
    from saga_orchestration.domain.timeout_id import TimeoutId


class InMemorySagaTimeoutRepository:
    """Timeouty na słownikach. Claim z lease, jak w SQL."""

    def __init__(self, store: SagaMemoryStore) -> None:
        self._store = store

    async def schedule(self, entry: SagaTimeout) -> None:
        self._store.timeouts[entry.timeout_id.value] = StoredTimeout(
            timeout_id=entry.timeout_id,
            saga_id=entry.saga_id,
            key=entry.key,
            step=entry.step,
            attempt=entry.attempt,
            kind=entry.kind,
            due_at=entry.due_at,
            status=TimeoutStatus.PENDING,
            owner=None,
            lease_until=None,
            correlation_id=entry.correlation_id,
            causation_id=entry.causation_id,
        )

    async def cancel_for_step(self, saga_id: SagaId, step: StepName) -> int:
        cancelled = 0
        for timeout_id, stored in self._store.timeouts.items():
            if (
                stored.saga_id == saga_id
                and stored.step == step
                and stored.status is TimeoutStatus.PENDING
            ):
                self._store.timeouts[timeout_id] = stored.with_status(TimeoutStatus.CANCELLED)
                cancelled += 1
        return cancelled

    async def cancel_for_saga(self, saga_id: SagaId) -> int:
        cancelled = 0
        for timeout_id, stored in self._store.timeouts.items():
            if stored.saga_id == saga_id and stored.status is TimeoutStatus.PENDING:
                self._store.timeouts[timeout_id] = stored.with_status(TimeoutStatus.CANCELLED)
                cancelled += 1
        return cancelled

    async def claim_due(
        self, *, owner: str, now: datetime, lease_until: datetime, limit: int
    ) -> tuple[ClaimedTimeout, ...]:
        due = sorted(
            (
                stored
                for stored in self._store.timeouts.values()
                if (
                    stored.status is TimeoutStatus.PENDING
                    and stored.due_at <= now
                    and (
                        stored.owner is None
                        or stored.lease_until is None
                        or stored.lease_until < now
                    )
                )
                or (
                    stored.status is TimeoutStatus.CLAIMED
                    and stored.lease_until is not None
                    and stored.lease_until < now
                )
            ),
            key=lambda stored: stored.due_at,
        )
        claimed: list[ClaimedTimeout] = []
        for stored in due[:limit]:
            self._store.timeouts[stored.timeout_id.value] = stored.claimed(owner, lease_until)
            claimed.append(
                ClaimedTimeout(
                    timeout_id=stored.timeout_id,
                    saga_id=stored.saga_id,
                    key=stored.key,
                    step=stored.step,
                    attempt=stored.attempt,
                    kind=stored.kind,
                    correlation_id=stored.correlation_id,
                    causation_id=stored.causation_id,
                )
            )
        return tuple(claimed)

    async def mark_done(self, timeout_id: TimeoutId) -> None:
        stored = self._store.timeouts.get(timeout_id.value)
        if stored is None or stored.status is not TimeoutStatus.CLAIMED:
            raise SagaGuardError(f"timeout {timeout_id.value} nie jest CLAIMED")
        self._store.timeouts[timeout_id.value] = stored.with_status(TimeoutStatus.DONE)
