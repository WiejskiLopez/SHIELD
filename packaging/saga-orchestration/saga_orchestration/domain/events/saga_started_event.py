from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from saga_orchestration.domain.base import DomainEvent

if TYPE_CHECKING:
    from datetime import datetime

    from saga_orchestration.domain.saga_id import SagaId
    from saga_orchestration.domain.saga_key import SagaKey


@dataclass(frozen=True, slots=True)
class SagaStartedEvent(DomainEvent):
    saga_id: SagaId
    key: SagaKey

    @classmethod
    def now(cls, *, saga_id: SagaId, key: SagaKey, at: datetime) -> SagaStartedEvent:
        return cls(occurred_at=at, saga_id=saga_id, key=key)
