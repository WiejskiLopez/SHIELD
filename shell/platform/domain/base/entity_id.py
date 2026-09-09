"""Podstawowa klasa identyfikatorów encji/agregatów (EntityId).

Wartość-obiekt reprezentujący unikalny identyfikator encji lub agregatu.
Niemutowalny, porównywany po wartości. Generowanie UUID v4 dostępne przez
metodę ``generate()``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Self

from shell.platform.domain.base.value_object import ValueObject
from shell.platform.domain.exceptions.domain_error import DomainError


@dataclass(frozen=True, slots=True)
class EntityId(ValueObject):
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise DomainError(f"{type(self).__name__} cannot be empty")

    def __str__(self) -> str:
        return self.value

    @classmethod
    def generate(cls) -> Self:
        return cls(str(uuid.uuid4()))