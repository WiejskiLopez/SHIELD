from __future__ import annotations

from dataclasses import dataclass

from saga_orchestration.domain.base import ValueObject
from saga_orchestration.domain.errors import SagaDomainError


@dataclass(frozen=True, slots=True)
class StepName(ValueObject):
    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) > 128:
            raise SagaDomainError(f"invalid step name: {self.value!r}")
