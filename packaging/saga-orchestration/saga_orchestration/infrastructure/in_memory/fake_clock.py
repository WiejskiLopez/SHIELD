from __future__ import annotations

from datetime import UTC, datetime, timedelta


class FakeClock:
    """Determinystyczny czas testów. Zawsze aware UTC (jak produkcyjna baza)."""

    def __init__(self, now: datetime | None = None) -> None:
        self._now = now if now is not None else datetime.now(UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now = self._now + delta


class FakeIds:
    """Determinystyczne id: prefix-1, prefix-2, ..."""

    def __init__(self, prefix: str = "id") -> None:
        self._prefix = prefix
        self._counter = 0

    def new_id(self) -> str:
        self._counter += 1
        return f"{self._prefix}-{self._counter}"
