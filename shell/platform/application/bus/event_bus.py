"""Szyna zdarzeń (EventBus) - publikuje zdarzenia do wielu subskrybentów."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from shell.platform.application.event_handlers.event_handler import EventHandler


class EventBus:
    """Publikuje zdarzenia domenowe do wielu subskrybentów."""

    def __init__(self) -> None:
        self._handler_factories: dict[type[object], list[Callable[[], EventHandler[Any]]]] = {}

    def subscribe(self, event_type: type[object], factory: Callable[[], EventHandler[Any]]) -> None:
        if event_type not in self._handler_factories:
            self._handler_factories[event_type] = []
        self._handler_factories[event_type].append(factory)

    async def publish(self, events: Sequence[object]) -> None:
        failures: list[Exception] = []
        for event in events:
            factories = self._handler_factories.get(type(event), [])
            for factory in factories:
                try:
                    handler = factory()
                    await handler.handle(event)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    failures.append(exc)
        if failures:
            raise failures[0]
