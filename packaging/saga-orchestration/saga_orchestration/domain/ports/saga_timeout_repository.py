from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime

    from saga_orchestration.domain.saga_id import SagaId
    from saga_orchestration.domain.saga_timeout import ClaimedTimeout, SagaTimeout
    from saga_orchestration.domain.step_name import StepName
    from saga_orchestration.domain.timeout_id import TimeoutId


class SagaTimeoutRepository(Protocol):
    """Port persystencji timeoutów. Claim atomowy należy do implementacji."""

    async def schedule(self, entry: SagaTimeout) -> None:
        """Wiersz PENDING. Idempotentny klucz dostarcza wywołujący (timeout_id)."""

    async def cancel_for_step(self, saga_id: SagaId, step: StepName) -> int:
        """PENDING -> CANCELLED dla kroku. Zwraca liczbę wierszy."""

    async def cancel_for_saga(self, saga_id: SagaId) -> int:
        """PENDING -> CANCELLED dla całej sagi (wejście terminalne)."""

    async def claim_due(
        self, *, owner: str, now: datetime, lease_until: datetime, limit: int
    ) -> tuple[ClaimedTimeout, ...]:
        """Atomowe przejęcie dojrzałych PENDING (UPDATE + odczyt własnych)."""

    async def mark_done(self, timeout_id: TimeoutId) -> None:
        """CLAIMED -> DONE po przetworzeniu w tej samej transakcji co efekt."""
