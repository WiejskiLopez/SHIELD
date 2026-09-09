"""Wyjątki platformy współdzielone przez warstwę domenową."""

from __future__ import annotations

from shell.platform.domain.exceptions.concurrent_modification_error import (
    ConcurrentModificationError,
)
from shell.platform.domain.exceptions.domain_conflict_error import DomainConflictError
from shell.platform.domain.exceptions.domain_error import DomainError

__all__ = [
    "ConcurrentModificationError",
    "DomainConflictError",
    "DomainError",
]