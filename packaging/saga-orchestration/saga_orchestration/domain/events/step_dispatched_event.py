from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from saga_orchestration.domain.base import DomainEvent

if TYPE_CHECKING:
    from datetime import datetime

    from saga_orchestration.domain.saga_id import SagaId
    from saga_orchestration.domain.step_attempt import StepAttempt


@dataclass(frozen=True, slots=True)
class StepDispatchedEvent(DomainEvent):
    """Każdy dispatch (pierwszy, retry, redispatch kompensaty) — attempt niesie krok."""

    saga_id: SagaId
    attempt: StepAttempt

    @classmethod
    def now(cls, *, saga_id: SagaId, attempt: StepAttempt, at: datetime) -> StepDispatchedEvent:
        return cls(occurred_at=at, saga_id=saga_id, attempt=attempt)
