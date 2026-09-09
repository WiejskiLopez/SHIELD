"""Klasa bazowa dla agregatów (Aggregate Root).

Agregaty posiadają prywatny bufor zdarzeń domenowych rejestrowanych
przez swoje metody. Warstwa aplikacji wywołuje ``pull_events`` po udanej
transakcji, aby przekazać je do wydawcy zdarzeń / outbox.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from shell.platform.domain.base.entity import Entity, TId

if TYPE_CHECKING:
    from shell.platform.domain.events import DomainEvent


class AggregateRoot(Entity[TId]):
    __slots__ = ("_events",)

    _events: list[DomainEvent]

    def __init__(self, id: TId) -> None:
        super().__init__(id)
        self._events = []

    def append_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events