"""Klasa bazowa dla obiektów wartości (Value Object).

Obiekty wartości są niemutowalne i porównywane po swojej strukturze
(wszystkie pola), a nie po tożsamości. Konkretne podklasy mają być
``@dataclass(frozen=True)`` lub ``StrEnum`` – zamrożony dataclass automatycznie
dostarcza ``__eq__``, ``__hash__``, ``__repr__`` i ``__slots__``.

Przykład::

    @dataclass(frozen=True, slots=True)
    class Status(ValueObject):
        value: str

        def __post_init__(self) -> None:
            if not self.value:
                raise ValueError("Status cannot be empty")
"""

from __future__ import annotations


class ValueObject:
    pass