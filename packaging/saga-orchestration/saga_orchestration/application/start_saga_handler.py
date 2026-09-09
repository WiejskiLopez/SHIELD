from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from saga_orchestration.domain.errors import SagaDomainError, SagaGuardError
from saga_orchestration.domain.ports.outbox_writer import OutboxCommandRow
from saga_orchestration.domain.saga import Saga
from saga_orchestration.domain.saga_id import SagaId
from saga_orchestration.domain.saga_payload import SagaPayload
from saga_orchestration.domain.saga_timeout import SagaTimeout
from saga_orchestration.domain.timeout_id import TimeoutId
from saga_orchestration.domain.timeout_kind import TimeoutKind

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime, timedelta

    from saga_orchestration.application.saga_unit_of_work import SagaUnitOfWork
    from saga_orchestration.application.step_dispatch import StepDispatchResolver
    from saga_orchestration.domain.ports.clock import Clock
    from saga_orchestration.domain.ports.id_generator import IdGenerator
    from saga_orchestration.domain.saga_key import SagaKey
    from saga_orchestration.domain.step import StepRegistry
    from saga_orchestration.domain.step_name import StepName


@dataclass(frozen=True, slots=True)
class StartSagaCommand:
    key: SagaKey
    payload: SagaPayload
    steps: StepRegistry
    correlation_id: str
    causation_id: str | None

    def __post_init__(self) -> None:
        if not self.correlation_id:
            raise SagaDomainError("start correlation_id jest wymagane")


class StartSagaHandler:
    """Start idempotentny: istnieje -> zwróć id; wyścig rozstrzyga reload."""

    def __init__(
        self,
        uow_factory: Callable[[], SagaUnitOfWork],
        clock: Clock,
        ids: IdGenerator,
        dispatch_resolver: StepDispatchResolver,
        source_service: str,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._ids = ids
        self._dispatch_resolver = dispatch_resolver
        self._source_service = source_service

    async def handle(self, command: StartSagaCommand) -> SagaId:
        uow = self._uow_factory()
        try:
            async with uow:
                existing = await uow.sagas.get_by_key(command.key)
                if existing is not None:
                    return existing.id
                now = self._clock.now()
                saga_id = SagaId(self._ids.new_id())
                saga = Saga.start(
                    saga_id=saga_id,
                    key=command.key,
                    payload=command.payload,
                    steps=command.steps,
                    now=now,
                )
                created = await uow.sagas.create(saga)
                if not created:
                    raced = await uow.sagas.get_by_key(command.key)
                    if raced is None:
                        raise SagaGuardError(
                            f"start przegrał wyścig i nie widzi sagi {command.key.business_key}"
                        )
                    return raced.id
                first = command.steps.steps[0]
                dispatch = self._dispatch_resolver.for_step(
                    command.key, command.payload, first.name, 1
                )
                command_id = f"{saga_id.value}:{first.name.value}:1"
                uow.append_command(
                    OutboxCommandRow(
                        command_id=command_id,
                        source_service=self._source_service,
                        destination_service=dispatch.destination_service,
                        contract_type=dispatch.contract_type,
                        schema_version=1,
                        aggregate_id=dispatch.aggregate_id,
                        payload={"command_id": command_id, **dispatch.payload},
                        correlation_id=command.correlation_id,
                        causation_id=command.causation_id,
                    )
                )
                await self._schedule_deadline(uow, saga, command, first.name, now)
                return saga.id
        finally:
            await uow.close()

    async def _schedule_deadline(
        self,
        uow: SagaUnitOfWork,
        saga: Saga,
        command: StartSagaCommand,
        step: StepName,
        now: datetime,
    ) -> None:
        definition = command.steps.by_name(step)
        if definition.timeout is None:
            return
        await uow.timeouts.schedule(
            SagaTimeout(
                timeout_id=TimeoutId(self._ids.new_id()),
                saga_id=saga.id,
                key=command.key,
                step=step,
                attempt=1,
                kind=TimeoutKind.RESULT_DEADLINE,
                due_at=now + definition.timeout,
                correlation_id=command.correlation_id,
                causation_id=command.causation_id,
            )
        )


def default_retry_due_at(now: datetime, backoff: timedelta | None) -> datetime:
    """Retry bez backoff -> natychmiast (due = now); z backoff -> odroczony."""
    if backoff is None:
        return now
    return now + backoff
