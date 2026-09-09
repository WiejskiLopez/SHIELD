from __future__ import annotations

from typing import TYPE_CHECKING

from saga_orchestration.application.timeout_saga_handler import (
    TimeoutSagaCommand,
    TimeoutSagaHandler,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import timedelta

    from saga_orchestration.application.saga_unit_of_work import SagaUnitOfWork
    from saga_orchestration.application.step_dispatch import StepDispatchResolver
    from saga_orchestration.domain.ports.clock import Clock
    from saga_orchestration.domain.ports.id_generator import IdGenerator


class SagaTimeoutWorker:
    """Claim (osobna transakcja) + jeden UoW na timeout. Błąd infra propaguje."""

    def __init__(
        self,
        uow_factory: Callable[[], SagaUnitOfWork],
        clock: Clock,
        dispatch_resolver: StepDispatchResolver,
        ids: IdGenerator,
        source_service: str,
        owner: str,
        lease: timedelta,
        batch_limit: int,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._dispatch_resolver = dispatch_resolver
        self._ids = ids
        self._source_service = source_service
        self._owner = owner
        self._lease = lease
        self._batch_limit = batch_limit

    async def run_once(self) -> int:
        now = self._clock.now()
        claim_uow = self._uow_factory()
        try:
            async with claim_uow:
                claimed = await claim_uow.timeouts.claim_due(
                    owner=self._owner,
                    now=now,
                    lease_until=now + self._lease,
                    limit=self._batch_limit,
                )
        finally:
            await claim_uow.close()
        for row in claimed:
            handler = TimeoutSagaHandler(
                self._uow_factory,
                self._clock,
                self._dispatch_resolver,
                self._ids,
                self._source_service,
            )
            await handler.handle(
                TimeoutSagaCommand(
                    timeout_id=row.timeout_id,
                    key=row.key,
                    step=row.step,
                    attempt=row.attempt,
                    kind=row.kind,
                    correlation_id=row.correlation_id,
                    causation_id=row.causation_id,
                )
            )
        return len(claimed)
