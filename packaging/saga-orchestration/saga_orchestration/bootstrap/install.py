from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from saga_orchestration.application.advance_saga_handler import AdvanceSagaHandler
from saga_orchestration.application.start_saga_handler import StartSagaHandler
from saga_orchestration.application.timeout_saga_handler import TimeoutSagaHandler
from saga_orchestration.infrastructure.saga_timeout_worker import SagaTimeoutWorker

if TYPE_CHECKING:
    from collections.abc import Callable

    from saga_orchestration.application.saga_unit_of_work import SagaUnitOfWork
    from saga_orchestration.application.step_dispatch import StepDispatchResolver
    from saga_orchestration.domain.ports.clock import Clock
    from saga_orchestration.domain.ports.id_generator import IdGenerator


@dataclass(frozen=True, slots=True)
class SagaWiring:
    uow_factory: Callable[[], SagaUnitOfWork]
    start_handler: StartSagaHandler
    advance_handler: AdvanceSagaHandler
    timeout_handler: TimeoutSagaHandler
    timeout_worker: SagaTimeoutWorker


def install_saga(
    *,
    uow_factory: Callable[[], SagaUnitOfWork],
    dispatch_resolver: StepDispatchResolver,
    clock: Clock,
    ids: IdGenerator,
    source_service: str,
    owner: str,
    lease: timedelta = timedelta(minutes=5),
    batch_limit: int = 100,
) -> SagaWiring:
    """Jedno podpięcie sagi U WŁAŚCICIELA typu (RFC-07).

    Fabrykę UoW (razem z sesjami i writerem) dostarcza serwis — cykl życia sesji
    to odpowiedzialność kompozycji, nie biblioteki. Serwisy bez sag nie wołają.
    """
    return SagaWiring(
        uow_factory=uow_factory,
        start_handler=StartSagaHandler(uow_factory, clock, ids, dispatch_resolver, source_service),
        advance_handler=AdvanceSagaHandler(
            uow_factory, clock, dispatch_resolver, ids, source_service
        ),
        timeout_handler=TimeoutSagaHandler(
            uow_factory, clock, dispatch_resolver, ids, source_service
        ),
        timeout_worker=SagaTimeoutWorker(
            uow_factory,
            clock,
            dispatch_resolver,
            ids,
            source_service,
            owner,
            lease,
            batch_limit,
        ),
    )
