"""Platform enum describing the explicit outbox delivery lifecycle."""

from __future__ import annotations

from enum import StrEnum

from shell.platform.domain.base.value_object import ValueObject


class OutboxStatus(ValueObject, StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SENT = "SENT"
    RETRY = "RETRY"
    DEAD_LETTER = "DEAD_LETTER"
