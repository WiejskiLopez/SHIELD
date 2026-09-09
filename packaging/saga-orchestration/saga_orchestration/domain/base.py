from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from datetime import datetime


class ValueObject:
    """Marker jak shell.platform.domain.base.value_object — własny, żeby nie zależeć od shell."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Niemutowalny fakt domenowy. Pola szczegółowe definiują podklasy (wyłącznie VO)."""

    occurred_at: datetime


TId = TypeVar("TId", bound=ValueObject)


class AggregateRoot(Generic[TId]):
    """Root tożsamościowy: równość i hash wyłącznie po ID, stan poza porównaniem."""

    __slots__ = ("_id", "_events")

    _id: TId
    _events: list[DomainEvent]

    def __init__(self, saga_id: TId) -> None:
        object.__setattr__(self, "_id", saga_id)
        object.__setattr__(self, "_events", [])

    @property
    def id(self) -> TId:
        return self._id

    def append_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AggregateRoot):
            return NotImplemented
        return type(self) is type(other) and self._id == other._id

    def __hash__(self) -> int:
        return hash((type(self).__name__, self._id))
