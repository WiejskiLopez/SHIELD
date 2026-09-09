from __future__ import annotations

from typing import TYPE_CHECKING

from saga_orchestration.infrastructure.in_memory.in_memory_saga_repository import (
    InMemorySagaRepository,
)
from saga_orchestration.infrastructure.in_memory.in_memory_saga_timeout_repository import (
    InMemorySagaTimeoutRepository,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from types import TracebackType

    from saga_orchestration.domain.ports.outbox_writer import OutboxCommandRow
    from saga_orchestration.domain.ports.saga_repository import SagaRepository
    from saga_orchestration.domain.ports.saga_timeout_repository import SagaTimeoutRepository
    from saga_orchestration.domain.processed_delivery import ProcessedDelivery
    from saga_orchestration.domain.step import StepRegistry
    from saga_orchestration.infrastructure.in_memory.in_memory_store import (
        SagaMemoryStore,
        StoredSaga,
        StoredTimeout,
    )


class InMemorySagaUnitOfWork:
    """UoW na snapshotach: enter kopiuje słowniki, rollback je przywraca."""

    def __init__(self, store: SagaMemoryStore, registries: Mapping[str, StepRegistry]) -> None:
        self._store = store
        self._sagas = InMemorySagaRepository(store, registries)
        self._timeouts = InMemorySagaTimeoutRepository(store)
        self._settled = False
        self._backup_sagas: dict[str, StoredSaga] = {}
        self._backup_keys: dict[tuple[str, str], str] = {}
        self._backup_deliveries: dict[str, ProcessedDelivery] = {}
        self._backup_timeouts: dict[str, StoredTimeout] = {}
        self._backup_outbox: list[OutboxCommandRow] = []

    async def __aenter__(self) -> InMemorySagaUnitOfWork:
        self._backup_sagas = dict(self._store.sagas)
        self._backup_keys = dict(self._store.keys)
        self._backup_deliveries = dict(self._store.deliveries)
        self._backup_timeouts = dict(self._store.timeouts)
        self._backup_outbox = list(self._store.outbox)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
            return
        if not self._settled:
            await self.commit()

    @property
    def sagas(self) -> SagaRepository:
        return self._sagas

    @property
    def timeouts(self) -> SagaTimeoutRepository:
        return self._timeouts

    def append_command(self, row: OutboxCommandRow) -> None:
        self._store.outbox.append(row)

    async def commit(self) -> None:
        self._settled = True

    async def rollback(self) -> None:
        self._store.sagas.clear()
        self._store.sagas.update(self._backup_sagas)
        self._store.keys.clear()
        self._store.keys.update(self._backup_keys)
        self._store.deliveries.clear()
        self._store.deliveries.update(self._backup_deliveries)
        self._store.timeouts.clear()
        self._store.timeouts.update(self._backup_timeouts)
        self._store.outbox.clear()
        self._store.outbox.extend(self._backup_outbox)
        self._settled = True

    async def close(self) -> None:
        return None
