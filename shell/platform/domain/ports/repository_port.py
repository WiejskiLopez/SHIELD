"""Generyczny port repozytorium – wspólny protokół dla wszystkich repozytoriów agregatów."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypeVar

if TYPE_CHECKING:
    from shell.platform.domain.value_objects.exists_result import ExistsResult

TAggregate = TypeVar("TAggregate")
TId = TypeVar("TId", contravariant=True)


class RepositoryPort(Protocol[TAggregate, TId]):
    """Minimalny generyczny protokół repozytorium.

    Każde repozytorium agregatu powinno rozszerzać ten protokół, aby
    gwarantować istnienie czterech kanonicznych operacji:
    get_by_id, save, delete, exists.
    """

    async def get_by_id(self, id: TId) -> TAggregate | None: ...

    async def save(self, entity: TAggregate) -> None: ...

    async def delete(self, id: TId) -> None: ...

    async def exists(self, id: TId) -> ExistsResult: ...