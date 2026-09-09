"""Błąd współbieżnej modyfikacji (ConcurrentModificationError).

Agregat został współbieżnie zmodyfikowany – wersja nie zgadza się przy zapisie.
"""

from __future__ import annotations

from shell.platform.domain.exceptions.domain_error import DomainError


class ConcurrentModificationError(DomainError):
    def __init__(self, aggregate_name: str, aggregate_id: str) -> None:
        super().__init__(
            f"{aggregate_name} was concurrently modified: id={aggregate_id!r}",
        )