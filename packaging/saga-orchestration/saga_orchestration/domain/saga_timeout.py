from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from saga_orchestration.domain.base import ValueObject
from saga_orchestration.domain.errors import SagaDomainError

if TYPE_CHECKING:
    from datetime import datetime

    from saga_orchestration.domain.saga_id import SagaId
    from saga_orchestration.domain.saga_key import SagaKey
    from saga_orchestration.domain.step_name import StepName
    from saga_orchestration.domain.timeout_id import TimeoutId
    from saga_orchestration.domain.timeout_kind import TimeoutKind


@dataclass(frozen=True, slots=True)
class SagaTimeout(ValueObject):
    """Wiersz timeoutu do zaplanowania. Status/owner/lease żyją w repozytorium."""

    timeout_id: TimeoutId
    saga_id: SagaId
    key: SagaKey
    step: StepName
    attempt: int
    kind: TimeoutKind
    due_at: datetime
    correlation_id: str
    causation_id: str | None

    def __post_init__(self) -> None:
        if self.attempt < 1:
            raise SagaDomainError(f"invalid attempt: {self.attempt!r}")
        if not self.correlation_id:
            raise SagaDomainError("timeout correlation_id jest wymagane")

    @property
    def delivery_id_value(self) -> str:
        """Stabilny delivery_id wyniku workerowego: reclaim daje duplikat, nie efekt."""
        return f"timeout:{self.timeout_id.value}"


@dataclass(frozen=True, slots=True)
class ClaimedTimeout(ValueObject):
    """Wiersz przejęty przez workera (claim już zacommitowany)."""

    timeout_id: TimeoutId
    saga_id: SagaId
    key: SagaKey
    step: StepName
    attempt: int
    kind: TimeoutKind
    correlation_id: str
    causation_id: str | None
