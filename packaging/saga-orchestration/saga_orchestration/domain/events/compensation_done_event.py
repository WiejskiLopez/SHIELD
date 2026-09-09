from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from saga_orchestration.domain.base import DomainEvent

if TYPE_CHECKING:
    from datetime import datetime

    from saga_orchestration.domain.saga_id import SagaId
    from saga_orchestration.domain.step_name import StepName


@dataclass(frozen=True, slots=True)
class CompensationDoneEvent(DomainEvent):
    saga_id: SagaId
    compensation: StepName

    @classmethod
    def now(cls, *, saga_id: SagaId, compensation: StepName, at: datetime) -> CompensationDoneEvent:
        return cls(occurred_at=at, saga_id=saga_id, compensation=compensation)
