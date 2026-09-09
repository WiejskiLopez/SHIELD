"""Unit tests for InMemoryUnitOfWorkBase rollback coherence."""

from __future__ import annotations

from typing import TypeVar

import pytest

from shell.platform.infrastructure.persistence.in_memory_repository import (
    InMemoryRepository,
)
from shell.platform.infrastructure.persistence.in_memory_unit_of_work import (
    InMemoryUnitOfWorkBase,
)
from shell.tests.shared.sample_aggregate import _SampleAggregate, _SampleId

TRepository = TypeVar("TRepository")


class _SharedStoreRepository(InMemoryRepository[_SampleAggregate, _SampleId]):
    """Repository sharing one store across instances (unstable factory target)."""

    def __init__(self, store: dict[str, _SampleAggregate]) -> None:
        self._store = store

    async def save(self, entity: _SampleAggregate) -> None:
        if entity.id.value == "second":
            raise RuntimeError("storage unavailable")
        await super().save(entity)


class _UnstableUnitOfWork(InMemoryUnitOfWorkBase):
    """Returns a NEW repository instance per call over a shared store."""

    def __init__(self, store: dict[str, _SampleAggregate]) -> None:
        super().__init__()
        self._shared_store = store

    def repository(self, repo_type: type[TRepository]) -> TRepository:
        repo = _SharedStoreRepository(self._shared_store)
        return repo  # type: ignore[return-value]


def _aggregate(label: str) -> _SampleAggregate:
    aggregate = _SampleAggregate(_SampleId(label), label)
    aggregate.do_something(label)
    return aggregate


class TestInMemoryRollbackCoherence:
    async def test_failed_commit_rolls_back_shared_store(self) -> None:
        store: dict[str, _SampleAggregate] = {}
        unit_of_work = _UnstableUnitOfWork(store)
        async with unit_of_work:
            await unit_of_work.save(_SampleAggregate, _aggregate("first"))
            with pytest.raises(RuntimeError, match="storage unavailable"):
                await unit_of_work.save(_SampleAggregate, _aggregate("second"))
                await unit_of_work.commit()

        assert store == {}
        assert unit_of_work.repository(_SampleAggregate).all() == []

    async def test_successful_commit_persists_all_saves(self) -> None:
        store: dict[str, _SampleAggregate] = {}
        unit_of_work = _UnstableUnitOfWork(store)
        async with unit_of_work:
            await unit_of_work.save(_SampleAggregate, _aggregate("first"))
            await unit_of_work.save(_SampleAggregate, _aggregate("third"))

        assert {aggregate.id.value for aggregate in store.values()} == {"first", "third"}
        assert len(unit_of_work.repository(_SampleAggregate).all()) == 2

    async def test_explicit_rollback_discards_pending_saves(self) -> None:
        store: dict[str, _SampleAggregate] = {}
        unit_of_work = _UnstableUnitOfWork(store)
        async with unit_of_work:
            await unit_of_work.save(_SampleAggregate, _aggregate("first"))
            await unit_of_work.rollback()

        assert store == {}

    def test_repository_factory_may_return_fresh_instances(self) -> None:
        store: dict[str, _SampleAggregate] = {}
        unit_of_work = _UnstableUnitOfWork(store)

        first = unit_of_work.repository(_SampleAggregate)
        second = unit_of_work.repository(_SampleAggregate)

        assert first is not second
