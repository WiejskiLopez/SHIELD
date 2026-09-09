"""OutboxBatchResult — strukturalny wynik jednego przebiegu outbox relay."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OutboxBatchResult:
    claimed_count: int
    processed_count: int
    retried_count: int
    dead_lettered_count: int
    failed_count: int
    duration_ms: int