from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from saga_orchestration.domain.base import DomainEvent

if TYPE_CHECKING:
    from datetime import datetime

    from saga_orchestration.domain.saga_id import SagaId


@dataclass(frozen=True, slots=True)
class SagaCompletedEvent(DomainEvent):
    saga_id: SagaId

    @classmethod
    def now(cls, *, saga_id: SagaId, at: datetime) -> SagaCompletedEvent:
        return cls(occurred_at=at, saga_id=saga_id)
