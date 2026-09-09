from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from saga_orchestration.domain.base import ValueObject
from saga_orchestration.domain.errors import SagaDomainError

if TYPE_CHECKING:
    from saga_orchestration.domain.step_name import StepName


@dataclass(frozen=True, slots=True)
class StepAttempt(ValueObject):
    """Konkretne wykonanie kroku: nazwa + numer próby (1-based)."""

    step: StepName
    attempt: int

    def __post_init__(self) -> None:
        if self.attempt < 1:
            raise SagaDomainError(f"invalid attempt: {self.attempt!r}")
