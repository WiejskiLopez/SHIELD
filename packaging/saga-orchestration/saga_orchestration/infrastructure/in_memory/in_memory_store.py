from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from saga_orchestration.domain.timeout_status import TimeoutStatus

if TYPE_CHECKING:
    from datetime import datetime

    from saga_orchestration.domain.ports.outbox_writer import OutboxCommandRow
    from saga_orchestration.domain.processed_delivery import ProcessedDelivery
    from saga_orchestration.domain.saga import Saga
    from saga_orchestration.domain.saga_id import SagaId
    from saga_orchestration.domain.saga_key import SagaKey
    from saga_orchestration.domain.saga_payload import SagaPayload
    from saga_orchestration.domain.saga_status import SagaStatus
    from saga_orchestration.domain.saga_version import SagaVersion
    from saga_orchestration.domain.step_attempt import StepAttempt
    from saga_orchestration.domain.step_name import StepName
    from saga_orchestration.domain.timeout_id import TimeoutId
    from saga_orchestration.domain.timeout_kind import TimeoutKind


@dataclass(frozen=True, slots=True)
class StoredSaga:
    """Niemutowalna migawka agregatu. Słowniki store kopiują się płytko i bezpiecznie."""

    saga_id: SagaId
    key: SagaKey
    payload: SagaPayload
    status: SagaStatus
    current_step: StepName | None
    completed: tuple[StepName, ...]
    failed: tuple[StepName, ...]
    compensation_stack: tuple[StepName, ...]
    compensation_cursor: int
    attempts: tuple[StepAttempt, ...]
    version: SagaVersion
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    failed_at: datetime | None
    compensated_at: datetime | None

    @classmethod
    def from_saga(cls, saga: Saga) -> StoredSaga:
        return cls(
            saga_id=saga.id,
            key=saga.key,
            payload=saga.payload,
            status=saga.status,
            current_step=saga.current_step,
            completed=saga.completed_steps,
            failed=saga.failed_steps,
            compensation_stack=saga.compensation_stack,
            compensation_cursor=saga.compensation_cursor,
            attempts=saga.attempts,
            version=saga.version,
            created_at=saga.created_at,
            updated_at=saga.updated_at,
            completed_at=saga.completed_at,
            failed_at=saga.failed_at,
            compensated_at=saga.compensated_at,
        )


@dataclass(frozen=True, slots=True)
class StoredTimeout:
    timeout_id: TimeoutId
    saga_id: SagaId
    key: SagaKey
    step: StepName
    attempt: int
    kind: TimeoutKind
    due_at: datetime
    status: TimeoutStatus
    owner: str | None
    lease_until: datetime | None
    correlation_id: str
    causation_id: str | None

    def claimed(self, owner: str, lease_until: datetime) -> StoredTimeout:
        from dataclasses import replace

        return replace(self, status=TimeoutStatus.CLAIMED, owner=owner, lease_until=lease_until)

    def with_status(self, status: TimeoutStatus) -> StoredTimeout:
        from dataclasses import replace

        return replace(self, status=status)


@dataclass(slots=True)
class SagaMemoryStore:
    """Współdzielony magazyn testowy. Wartości niemutowalne — snapshot to płytkie kopie."""

    sagas: dict[str, StoredSaga] = field(default_factory=dict)
    keys: dict[tuple[str, str], str] = field(default_factory=dict)
    deliveries: dict[str, ProcessedDelivery] = field(default_factory=dict)
    timeouts: dict[str, StoredTimeout] = field(default_factory=dict)
    outbox: list[OutboxCommandRow] = field(default_factory=list)
