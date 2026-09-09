from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from saga_orchestration.domain.processed_delivery import DeliveryId, ProcessedDelivery
    from saga_orchestration.domain.saga import Saga
    from saga_orchestration.domain.saga_id import SagaId
    from saga_orchestration.domain.saga_key import SagaKey
    from saga_orchestration.domain.saga_version import SagaVersion


class SagaRepository(Protocol):
    """Port persystencji instancji + dziennika. Zero sesji w sygnaturach."""

    async def get_by_key(self, key: SagaKey) -> Saga | None:
        """Odtwórz agregat ze stosem/kursorem. None gdy brak."""

    async def create(self, saga: Saga) -> bool:
        """INSERT ... ON CONFLICT DO NOTHING. True = nowy wiersz, False = wyścig."""

    async def store(self, saga: Saga, *, persisted_version: SagaVersion) -> None:
        """UPDATE ... WHERE version = :persisted_version. Pudło -> SagaVersionConflictError."""

    async def is_delivery_processed(self, saga_id: SagaId, delivery_id: DeliveryId) -> bool:
        """Czy delivery_id jest w dzienniku (RFC-01, reguła 1)."""

    async def try_record_delivery(self, entry: ProcessedDelivery) -> bool:
        """ON CONFLICT DO NOTHING (PG i SQLite). True = nowy wpis."""
