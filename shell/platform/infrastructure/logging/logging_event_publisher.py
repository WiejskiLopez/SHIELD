"""LoggingEventPublisher — publikuje zdarzenia domenowe przez port Logger."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from shell.platform.application.ports.logger import Logger


class LoggingEventPublisher:
    """Adapter EventPublisher, który loguje każde zdarzenie domenowe jako wpis JSON."""

    def __init__(self, logger: Logger) -> None:
        self._logger = logger

    async def publish(self, events: Sequence[object]) -> None:
        for event in events:
            self._logger.info(
                "domain_event",
                event_type=type(event).__name__,
                occurred_at=event.occurred_at.value.isoformat(),  # type: ignore[attr-defined]
            )