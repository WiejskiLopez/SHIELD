"""Zdarzenie domenowe (DomainEvent).

Niemutowalny fakt, który się wydarzył. Nosi identyfikator zdarzenia,
identyfikator agregatu, który go wyemitował, oraz czas wystąpienia.
Nazwa klasy zdarzenia zawsze w czasie przeszłym (np. UserCreatedEvent).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from shell.platform.domain.value_objects.event_id import EventId

if TYPE_CHECKING:
    from shell.platform.domain.value_objects.occurred_at import OccurredAt


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    event_id: EventId = field(default_factory=EventId.generate)
    occurred_at: OccurredAt