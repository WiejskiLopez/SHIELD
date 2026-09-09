from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from saga_orchestration.domain.base import ValueObject
from saga_orchestration.domain.errors import SagaDomainError

if TYPE_CHECKING:
    from datetime import timedelta

    from saga_orchestration.domain.step_name import StepName


@dataclass(frozen=True, slots=True)
class StepDefinition(ValueObject):
    """Definicja kroku: dokąd, czym cofnąć, ile prób, jak długo czekać na wynik."""

    name: StepName
    target_service: str
    compensation_step: StepName | None = None
    timeout: timedelta | None = None
    max_attempts: int = 1
    backoff: timedelta | None = None

    def __post_init__(self) -> None:
        if not self.target_service:
            raise SagaDomainError("target_service wymagany")
        if self.max_attempts < 1:
            raise SagaDomainError("max_attempts >= 1")
        if self.timeout is not None and self.timeout.total_seconds() <= 0:
            raise SagaDomainError("timeout musi być dodatni")
        if self.backoff is not None and self.backoff.total_seconds() < 0:
            raise SagaDomainError("backoff nie może być ujemny")


@dataclass(frozen=True, slots=True)
class StepRegistry(ValueObject):
    steps: tuple[StepDefinition, ...]

    def __post_init__(self) -> None:
        if not self.steps:
            raise SagaDomainError("saga bez kroków nie istnieje")
        names = [step.name for step in self.steps]
        if len(set(names)) != len(names):
            raise SagaDomainError("duplikat kroku w registry")

    def by_name(self, name: StepName) -> StepDefinition:
        for step in self.steps:
            if step.name == name:
                return step
        raise SagaDomainError(f"nieznany krok: {name.value!r}")

    def contains(self, name: StepName) -> bool:
        return any(step.name == name for step in self.steps)
