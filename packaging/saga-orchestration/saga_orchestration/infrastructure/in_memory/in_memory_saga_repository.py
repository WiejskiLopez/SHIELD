from __future__ import annotations

from typing import TYPE_CHECKING

from saga_orchestration.domain.errors import SagaGuardError, SagaVersionConflictError
from saga_orchestration.domain.saga import Saga
from saga_orchestration.infrastructure.in_memory.in_memory_store import StoredSaga

if TYPE_CHECKING:
    from collections.abc import Mapping

    from saga_orchestration.domain.processed_delivery import DeliveryId, ProcessedDelivery
    from saga_orchestration.domain.saga_id import SagaId
    from saga_orchestration.domain.saga_key import SagaKey
    from saga_orchestration.domain.saga_version import SagaVersion
    from saga_orchestration.domain.step import StepRegistry
    from saga_orchestration.infrastructure.in_memory.in_memory_store import SagaMemoryStore


class InMemorySagaRepository:
    """Port na słownikach. Semantyka 1:1 z SQL (UNIQUE, version check, dziennik)."""

    def __init__(self, store: SagaMemoryStore, registries: Mapping[str, StepRegistry]) -> None:
        self._store = store
        self._registries = registries

    async def get_by_key(self, key: SagaKey) -> Saga | None:
        saga_id = self._store.keys.get((key.saga_type, key.business_key))
        if saga_id is None:
            return None
        stored = self._store.sagas.get(saga_id)
        if stored is None:
            return None
        return self._to_domain(stored)

    async def create(self, saga: Saga) -> bool:
        if (saga.key.saga_type, saga.key.business_key) in self._store.keys:
            return False
        self._store.sagas[saga.id.value] = StoredSaga.from_saga(saga)
        self._store.keys[(saga.key.saga_type, saga.key.business_key)] = saga.id.value
        return True

    async def store(self, saga: Saga, *, persisted_version: SagaVersion) -> None:
        stored = self._store.sagas.get(saga.id.value)
        if stored is None or stored.version.value != persisted_version.value:
            raise SagaVersionConflictError(
                f"saga {saga.id.value} zmieniła się (oczekiwano v{persisted_version.value})"
            )
        self._store.sagas[saga.id.value] = StoredSaga.from_saga(saga)

    async def is_delivery_processed(self, saga_id: SagaId, delivery_id: DeliveryId) -> bool:
        entry = self._store.deliveries.get(delivery_id.value)
        return entry is not None and entry.saga_id == saga_id

    async def try_record_delivery(self, entry: ProcessedDelivery) -> bool:
        if entry.delivery_id.value in self._store.deliveries:
            return False
        self._store.deliveries[entry.delivery_id.value] = entry
        return True

    def _to_domain(self, stored: StoredSaga) -> Saga:
        registry = self._registries.get(stored.key.saga_type)
        if registry is None:
            raise SagaGuardError(f"nieznany saga_type w store: {stored.key.saga_type!r}")
        return Saga.restore(
            saga_id=stored.saga_id,
            key=stored.key,
            payload=stored.payload,
            steps=registry,
            status=stored.status,
            current_step=stored.current_step,
            completed=stored.completed,
            failed=stored.failed,
            compensation_stack=stored.compensation_stack,
            compensation_cursor=stored.compensation_cursor,
            attempts=stored.attempts,
            version=stored.version,
            created_at=stored.created_at,
            updated_at=stored.updated_at,
            completed_at=stored.completed_at,
            failed_at=stored.failed_at,
            compensated_at=stored.compensated_at,
        )
