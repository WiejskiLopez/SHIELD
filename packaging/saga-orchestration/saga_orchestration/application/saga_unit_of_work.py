from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from types import TracebackType

    from saga_orchestration.domain.ports.outbox_writer import OutboxCommandRow
    from saga_orchestration.domain.ports.saga_repository import SagaRepository
    from saga_orchestration.domain.ports.saga_timeout_repository import SagaTimeoutRepository


class SagaUnitOfWork(Protocol):
    """Jedna transakcja: saga + outbox + timeouty + dziennik. Sesja z serwisu."""

    async def __aenter__(self) -> SagaUnitOfWork:
        """Wejście bez efektów — żadnych zapytań w enter."""

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Wyjątek -> rollback ZAWSZE. Czyste wyjście bez commit -> commit."""

    @property
    def sagas(self) -> SagaRepository:
        """Repozytorium instancji i dziennika, związane z sesją tego UoW."""

    @property
    def timeouts(self) -> SagaTimeoutRepository:
        """Repozytorium timeoutów, związane z sesją tego UoW."""

    def append_command(self, row: OutboxCommandRow) -> None:
        """Wiersz command_outbox do TEJ SAMEJ sesji. Bez flush poza UoW."""

    async def commit(self) -> None:
        """Flush + commit. Raz."""

    async def rollback(self) -> None:
        """Rollback. Idempotentny."""

    async def close(self) -> None:
        """Zamknięcie sesji gdy UoW jest jej właścicielem; inaczej no-op."""
