from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from saga_orchestration.domain.base import ValueObject
from saga_orchestration.domain.errors import SagaDomainError

if TYPE_CHECKING:
    from datetime import datetime

    from saga_orchestration.domain.saga_id import SagaId
    from saga_orchestration.domain.step_name import StepName


@dataclass(frozen=True, slots=True)
class DeliveryId(ValueObject):
    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) > 128:
            raise SagaDomainError(f"invalid delivery_id: {self.value!r}")


@dataclass(frozen=True, slots=True)
class ProcessedDelivery(ValueObject):
    """Wpis dziennika dowożeń: wynik próby zastosowany dokładnie raz (RFC-01)."""

    saga_id: SagaId
    delivery_id: DeliveryId
    step: StepName
    attempt: int
    succeeded: bool
    processed_at: datetime

    def __post_init__(self) -> None:
        if self.attempt < 1:
            raise SagaDomainError(f"invalid attempt: {self.attempt!r}")
