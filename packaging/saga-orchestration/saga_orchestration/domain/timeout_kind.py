from __future__ import annotations

from enum import StrEnum


class TimeoutKind(StrEnum):
    """Rodzaj wiersza timeoutu: deadline wyniku albo odroczony retry."""

    RESULT_DEADLINE = "result_deadline"
    RETRY_DELAY = "retry_delay"
