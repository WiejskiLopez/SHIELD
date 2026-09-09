from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from saga_orchestration.application.start_saga_handler import default_retry_due_at
from saga_orchestration.domain.errors import SagaDomainError, SagaGuardError
from saga_orchestration.domain.ports.outbox_writer import OutboxCommandRow
from saga_orchestration.domain.processed_delivery import DeliveryId, ProcessedDelivery
from saga_orchestration.domain.saga_status import SagaStatus
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
    from saga_orchestration.domain.saga_version import SagaVersion
    from saga_orchestration.domain.step_name import StepName


@dataclass(frozen=True, slots=True)
class TimeoutSagaCommand:
    timeout_id: TimeoutId
    key: SagaKey
    step: StepName
    attempt: int
    kind: TimeoutKind
    correlation_id: str
    causation_id: str | None

    def __post_init__(self) -> None:
        if self.attempt < 1:
            raise SagaDomainError(f"timeout attempt >= 1, jest {self.attempt}")
        if not self.correlation_id:
            raise SagaDomainError("timeout correlation_id jest wymagane")


class TimeoutSagaHandler:
    """Efekt przejętego timeoutu: redispatch retry albo failure próby. Zawsze DONE."""

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

    async def handle(self, command: TimeoutSagaCommand) -> None:
        uow = self._uow_factory()
        try:
            async with uow:
                saga = await uow.sagas.get_by_key(command.key)
                if saga is None:
                    await uow.timeouts.mark_done(command.timeout_id)
                    return
                now = self._clock.now()
                persisted = saga.version
                if command.kind is TimeoutKind.RETRY_DELAY:
                    await self._fire_retry(uow, saga, command, persisted, now)
                else:
                    await self._fire_deadline(uow, saga, command, persisted, now)
                await uow.timeouts.mark_done(command.timeout_id)
        finally:
            await uow.close()

    async def _fire_retry(
        self,
        uow: SagaUnitOfWork,
        saga: Saga,
        command: TimeoutSagaCommand,
        persisted: SagaVersion,
        now: datetime,
    ) -> None:
        if not self._is_retry_live(saga, command):
            return
        if saga.status is SagaStatus.COMPENSATING:
            saga.on_compensation_redispatched(command.step, command.attempt, now=now)
        else:
            saga.on_retry_dispatched(command.step, command.attempt, now=now)
        await uow.sagas.store(saga, persisted_version=persisted)
        dispatch = self._dispatch_resolver.for_step(
            saga.key, saga.payload, command.step, command.attempt
        )
        command_id = f"{saga.id.value}:{command.step.value}:{command.attempt}"
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
        await self._schedule_deadline(uow, saga, command, now)

    def _is_retry_live(self, saga: Saga, command: TimeoutSagaCommand) -> bool:
        if saga.is_terminal or saga.current_step != command.step:
            return False
        if saga.status is SagaStatus.COMPENSATING:
            if saga.compensation_cursor >= len(saga.compensation_stack):
                return False
            if saga.compensation_stack[saga.compensation_cursor] != command.step:
                return False
        return saga.attempt_of(command.step) == command.attempt - 1

    async def _fire_deadline(
        self,
        uow: SagaUnitOfWork,
        saga: Saga,
        command: TimeoutSagaCommand,
        persisted: SagaVersion,
        now: datetime,
    ) -> None:
        delivery_id = DeliveryId(f"timeout:{command.timeout_id.value}")
        if await uow.sagas.is_delivery_processed(saga.id, delivery_id):
            return
        if saga.is_terminal or saga.current_step != command.step:
            return
        if saga.attempt_of(command.step) != command.attempt:
            return
        if saga.status is SagaStatus.COMPENSATING:
            if (
                saga.compensation_cursor >= len(saga.compensation_stack)
                or saga.compensation_stack[saga.compensation_cursor] != command.step
            ):
                return
            saga.on_compensation_failed(command.step, command.attempt, now=now)
            await uow.timeouts.cancel_for_step(saga.id, command.step)
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
        else:
            target = saga.on_step_failed(command.step, command.attempt, now=now, timed_out=True)
            await uow.timeouts.cancel_for_step(saga.id, command.step)
            if target is None:
                await uow.timeouts.cancel_for_saga(saga.id)
            elif target == command.step:
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
            else:
                await self._dispatch_compensation_now(uow, saga, command, target, now)
        await uow.sagas.store(saga, persisted_version=persisted)
        recorded = await uow.sagas.try_record_delivery(
            ProcessedDelivery(
                saga_id=saga.id,
                delivery_id=delivery_id,
                step=command.step,
                attempt=command.attempt,
                succeeded=False,
                processed_at=now,
            )
        )
        if not recorded:
            raise SagaGuardError(f"wyścig dowożenia {delivery_id.value}")

    async def _dispatch_compensation_now(
        self,
        uow: SagaUnitOfWork,
        saga: Saga,
        command: TimeoutSagaCommand,
        target: StepName,
        now: datetime,
    ) -> None:
        dispatch = self._dispatch_resolver.for_step(saga.key, saga.payload, target, 1)
        command_id = f"{saga.id.value}:{target.value}:1"
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
        trigger = saga.failed_steps[-1]
        trigger_timeout = saga.steps.by_name(trigger).timeout
        if trigger_timeout is None:
            return
        await uow.timeouts.schedule(
            SagaTimeout(
                timeout_id=TimeoutId(self._ids.new_id()),
                saga_id=saga.id,
                key=saga.key,
                step=target,
                attempt=1,
                kind=TimeoutKind.RESULT_DEADLINE,
                due_at=now + trigger_timeout,
                correlation_id=command.correlation_id,
                causation_id=command.causation_id,
            )
        )

    async def _schedule_deadline(
        self, uow: SagaUnitOfWork, saga: Saga, command: TimeoutSagaCommand, now: datetime
    ) -> None:
        timeout = self._deadline_for(saga, command.step)
        if timeout is None:
            return
        await uow.timeouts.schedule(
            SagaTimeout(
                timeout_id=TimeoutId(self._ids.new_id()),
                saga_id=saga.id,
                key=saga.key,
                step=command.step,
                attempt=command.attempt,
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
