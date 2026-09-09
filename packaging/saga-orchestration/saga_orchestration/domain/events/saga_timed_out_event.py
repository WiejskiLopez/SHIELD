from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from saga_orchestration.domain.base import DomainEvent

if TYPE_CHECKING:
    from datetime import datetime

    from saga_orchestration.domain.saga_id import SagaId
    from saga_orchestration.domain.step_attempt import StepAttempt


@dataclass(frozen=True, slots=True)
class SagaTimedOutEvent(DomainEvent):
    """Deadline próby minął bez wyniku. Handler traktuje jak failure tej próby."""

    saga_id: SagaId
    attempt: StepAttempt

    @classmethod
    def now(cls, *, saga_id: SagaId, attempt: StepAttempt, at: datetime) -> SagaTimedOutEvent:
        return cls(occurred_at=at, saga_id=saga_id, attempt=attempt)
