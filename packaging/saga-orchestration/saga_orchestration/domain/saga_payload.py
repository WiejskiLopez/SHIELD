from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from saga_orchestration.domain.base import ValueObject
from saga_orchestration.domain.errors import SagaDomainError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from saga_orchestration.domain.json_value import JsonValue


@dataclass(frozen=True, slots=True)
class SagaPayload(ValueObject):
    """Nieprzezroczyste dane korelacyjne sagi. Kopia obronna przy konstrukcji."""

    data: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        if not isinstance(self.data, dict):
            raise SagaDomainError("saga payload musi być słownikiem")
        object.__setattr__(self, "data", dict(self.data))

    @classmethod
    def empty(cls) -> SagaPayload:
        return cls({})
