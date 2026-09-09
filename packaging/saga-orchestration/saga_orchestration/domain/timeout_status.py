from __future__ import annotations

from enum import StrEnum


class TimeoutStatus(StrEnum):
    """Cykl życia wiersza timeoutu: oczekuje, przejęty, zrobiony, anulowany."""

    PENDING = "pending"
    CLAIMED = "claimed"
    DONE = "done"
    CANCELLED = "cancelled"
