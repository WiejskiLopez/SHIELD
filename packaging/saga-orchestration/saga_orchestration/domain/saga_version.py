from __future__ import annotations

from dataclasses import dataclass

from saga_orchestration.domain.base import ValueObject
from saga_orchestration.domain.errors import SagaDomainError


@dataclass(frozen=True, slots=True)
class SagaVersion(ValueObject):
    """Wersja optymistycznego blokowania. Rosnąca wyłącznie przez next()."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise SagaDomainError(f"invalid saga version: {self.value!r}")

    def next(self) -> SagaVersion:
        return SagaVersion(self.value + 1)

    @classmethod
    def initial(cls) -> SagaVersion:
        return cls(1)
