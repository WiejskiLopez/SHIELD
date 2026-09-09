"""Błąd konfliktu domenowego (DomainConflictError).

Klasa bazowa dla naruszeń reguł domenowych oznaczających konflikt stanu
(np. zasób już istnieje, jest już usunięty lub wersjonowanie się nie zgadza).
Mapowana na HTTP 409 Conflict (obok ConcurrentModificationError).
"""

from __future__ import annotations

from shell.platform.domain.exceptions.domain_error import DomainError


class DomainConflictError(DomainError):
    pass
