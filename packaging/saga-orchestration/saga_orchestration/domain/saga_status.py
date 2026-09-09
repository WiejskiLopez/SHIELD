from __future__ import annotations

from enum import StrEnum


class SagaStatus(StrEnum):
    """Stan instancji sagi. Czysty StrEnum (mixin z markerem VO nie działa na 3.14)."""

    CREATED = "created"
    RUNNING = "running"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    COMPLETED = "completed"
    FAILED = "failed"
