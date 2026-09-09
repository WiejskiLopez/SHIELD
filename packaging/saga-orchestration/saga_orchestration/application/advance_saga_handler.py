from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from saga_orchestration.application.start_saga_handler import default_retry_due_at
from saga_orchestration.domain.errors import SagaDomainError, SagaGuardError
from saga_orchestration.domain.ports.outbox_writer import OutboxCommandRow
from saga_orchestration.domain.processed_delivery import DeliveryId, ProcessedDelivery
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
    from saga_orchestration.domain.saga import Saga
    from saga_orchestration.domain.saga_key import SagaKey
    from saga_orchestration.domain.step_name import StepName


@dataclass(frozen=True, slots=True)
class AdvanceSagaCommand:
    key: SagaKey
    delivery_id: DeliveryId
    step: StepName
    attempt: int
    succeeded: bool
    is_compensation: bool
    correlation_id: str
    causation_id: str | None

    def __post_init__(self) -> None:
        if self.attempt < 1:
            raise SagaDomainError(f"advance attempt >= 1, jest {self.attempt}")
        if not self.correlation_id:
            raise SagaDomainError("advance correlation_id jest wymagane")


class AdvanceSagaHandler:
    """Wynik kroku -> następny krok albo kompensacja. Idempotentny (dziennik)."""

    def __init__(
        self,
        uow_factory: Callable[[], SagaUnitOfWork],
        clock: Clock,
        dispatch_resolver: StepDispatchResolver,
        ids: IdGenerator,
        source_service: str,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._dispatch_resolver = dispatch_resolver
        self._ids = ids
        self._source_service = source_service

    async def handle(self, command: AdvanceSagaCommand) -> None:
        uow = self._uow_factory()
        try:
            async with uow:
                saga = await uow.sagas.get_by_key(command.key)
                if saga is None:
                    return
                if await uow.sagas.is_delivery_processed(saga.id, command.delivery_id):
                    return
                if not self._is_current(saga, command):
                    return
                now = self._clock.now()
                persisted = saga.version
                if command.is_compensation:
                    await self._apply_compensation_result(uow, saga, command, now)
                elif command.succeeded:
                    await self._apply_step_success(uow, saga, command, now)
                else:
                    await self._apply_step_failure(uow, saga, command, now, timed_out=False)
                await uow.sagas.store(saga, persisted_version=persisted)
                recorded = await uow.sagas.try_record_delivery(
                    ProcessedDelivery(
                        saga_id=saga.id,
                        delivery_id=command.delivery_id,
                        step=command.step,
                        attempt=command.attempt,
                        succeeded=command.succeeded,
                        processed_at=now,
                    )
                )
                if not recorded:
                    raise SagaGuardError(f"wyścig dowożenia {command.delivery_id.value}")
        finally:
            await uow.close()

    def _is_current(self, saga: Saga, command: AdvanceSagaCommand) -> bool:
        if saga.is_terminal or saga.current_step != command.step:
            return False
        return saga.attempt_of(command.step) == command.attempt

    async def _apply_step_success(
        self, uow: SagaUnitOfWork, saga: Saga, command: AdvanceSagaCommand, now: datetime
    ) -> None:
        nxt = saga.on_step_succeeded(command.step, command.attempt, now=now)
        await uow.timeouts.cancel_for_step(saga.id, command.step)
        if nxt is None:
            await uow.timeouts.cancel_for_saga(saga.id)
            return
        await self._dispatch_now(uow, saga, command, nxt, attempt=1, now=now)

    async def _apply_step_failure(
        self,
        uow: SagaUnitOfWork,
        saga: Saga,
        command: AdvanceSagaCommand,
        now: datetime,
        *,
        timed_out: bool,
    ) -> None:
        target = saga.on_step_failed(command.step, command.attempt, now=now, timed_out=timed_out)
        await uow.timeouts.cancel_for_step(saga.id, command.step)
        if target is None:
            await uow.timeouts.cancel_for_saga(saga.id)
            return
        if target == command.step:
            definition = saga.steps.by_name(command.step)
            await uow.timeouts.schedule(
                SagaTimeout(
                    timeout_id=TimeoutId(self._ids.new_id()),
                    saga_id=saga.id,
                    key=saga.key,
                    step=command.step,
                    attempt=command.attempt + 1,
                    kind=TimeoutKind.RETRY_DELAY,
                    due_at=default_retry_due_at(now, definition.backoff),
                    correlation_id=command.correlation_id,
                    causation_id=command.causation_id,
                )
            )
            return
        await self._dispatch_now(uow, saga, command, target, attempt=1, now=now)

    async def _apply_compensation_result(
        self, uow: SagaUnitOfWork, saga: Saga, command: AdvanceSagaCommand, now: datetime
    ) -> None:
        if command.succeeded:
            nxt = saga.on_compensation_done(command.step, command.attempt, now=now)
        else:
            saga.on_compensation_failed(command.step, command.attempt, now=now)
            nxt = command.step
        await uow.timeouts.cancel_for_step(saga.id, command.step)
        if nxt is None:
            await uow.timeouts.cancel_for_saga(saga.id)
            return
        if nxt == command.step and not command.succeeded:
            trigger = saga.failed_steps[-1]
            backoff = saga.steps.by_name(trigger).backoff
            await uow.timeouts.schedule(
                SagaTimeout(
                    timeout_id=TimeoutId(self._ids.new_id()),
                    saga_id=saga.id,
                    key=saga.key,
                    step=command.step,
                    attempt=command.attempt + 1,
                    kind=TimeoutKind.RETRY_DELAY,
                    due_at=default_retry_due_at(now, backoff),
                    correlation_id=command.correlation_id,
                    causation_id=command.causation_id,
                )
            )
            return
        await self._dispatch_now(uow, saga, command, nxt, attempt=1, now=now)

    async def _dispatch_now(
        self,
        uow: SagaUnitOfWork,
        saga: Saga,
        command: AdvanceSagaCommand,
        step: StepName,
        *,
        attempt: int,
        now: datetime,
    ) -> None:
        dispatch = self._dispatch_resolver.for_step(saga.key, saga.payload, step, attempt)
        command_id = f"{saga.id.value}:{step.value}:{attempt}"
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
        await self._schedule_deadline(uow, saga, command, step, attempt, now)

    async def _schedule_deadline(
        self,
        uow: SagaUnitOfWork,
        saga: Saga,
        command: AdvanceSagaCommand,
        step: StepName,
        attempt: int,
        now: datetime,
    ) -> None:
        timeout = self._deadline_for(saga, step)
        if timeout is None:
            return
        await uow.timeouts.schedule(
            SagaTimeout(
                timeout_id=TimeoutId(self._ids.new_id()),
                saga_id=saga.id,
                key=saga.key,
                step=step,
                attempt=attempt,
                kind=TimeoutKind.RESULT_DEADLINE,
                due_at=now + timeout,
                correlation_id=command.correlation_id,
                causation_id=command.causation_id,
            )
        )

    def _deadline_for(self, saga: Saga, step: StepName) -> timedelta | None:
        if saga.steps.contains(step):
            return saga.steps.by_name(step).timeout
        if saga.failed_steps:
            return saga.steps.by_name(saga.failed_steps[-1]).timeout
        return None
