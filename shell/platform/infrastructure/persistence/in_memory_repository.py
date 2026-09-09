"""Generic in-memory repository — shared base for all InMemory* repositories."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from shell.platform.domain.value_objects.exists_result import ExistsResult

if TYPE_CHECKING:
    from datetime import datetime

TAggregate = TypeVar("TAggregate")
TId = TypeVar("TId")


class InMemoryRepository[TAggregate, TId]:
    """Base in-memory repository.

    Provides common get_by_id / save / delete / exists backed by a
    simple ``dict[str, TAggregate]``.  Concrete subclasses only need
    to provide BC-specific query methods.

    ``delete`` physically removes the record. Domain-level soft-delete is
    performed by the aggregate and persisted through ``save``.
    ``exists`` returns ``False`` for aggregates already marked as deleted.
    """

    def __init__(self) -> None:
        self._store: dict[str, TAggregate] = {}

    async def get_by_id(self, id: TId) -> TAggregate | None:
        key = id.value if hasattr(id, "value") else str(id)
        entity = self._store.get(key)
        if entity is None or self._is_deleted(entity):
            return None
        return entity

    @staticmethod
    def _is_deleted(entity: TAggregate) -> bool:
        deleted = getattr(entity, "_deleted_at", None)
        if deleted is None:
            return False
        return getattr(deleted, "value", None) is not None

    def _visible_values(self) -> list[TAggregate]:
        return [entity for entity in self._store.values() if not self._is_deleted(entity)]

    def all(self) -> list[TAggregate]:
        """Return a copy of all visible aggregates."""
        return self._visible_values()

    async def save(self, entity: TAggregate) -> None:
        key = entity.id.value if hasattr(entity.id, "value") else str(entity.id)  # type: ignore[attr-defined]
        self._store[key] = entity

    # Contract: aggregate.delete() is soft-delete; repository.delete() is hard-delete.
    async def delete(self, id: TId, now: datetime | None = None) -> None:
        key = id.value if hasattr(id, "value") else str(id)
        self._store.pop(key, None)

    async def exists(self, id: TId) -> ExistsResult:
        key = id.value if hasattr(id, "value") else str(id)
        entity = self._store.get(key)
        if entity is None:
            return ExistsResult(False)
        deleted = getattr(entity, "_deleted_at", None)
        if deleted is None:
            return ExistsResult(True)
        deleted_value = getattr(deleted, "value", None)
        return ExistsResult(deleted_value is None)
