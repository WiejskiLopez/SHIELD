from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Self

from saga_orchestration.domain.base import AggregateRoot
from saga_orchestration.domain.errors import SagaGuardError
from saga_orchestration.domain.events.compensation_done_event import CompensationDoneEvent
from saga_orchestration.domain.events.compensation_started_event import CompensationStartedEvent
from saga_orchestration.domain.events.saga_compensated_event import SagaCompensatedEvent
from saga_orchestration.domain.events.saga_completed_event import SagaCompletedEvent
from saga_orchestration.domain.events.saga_failed_event import SagaFailedEvent
from saga_orchestration.domain.events.saga_started_event import SagaStartedEvent
from saga_orchestration.domain.events.saga_timed_out_event import SagaTimedOutEvent
from saga_orchestration.domain.events.step_dispatched_event import StepDispatchedEvent
from saga_orchestration.domain.events.step_failed_event import StepFailedEvent
from saga_orchestration.domain.events.step_succeeded_event import StepSucceededEvent
from saga_orchestration.domain.saga_id import SagaId
from saga_orchestration.domain.saga_status import SagaStatus
from saga_orchestration.domain.saga_version import SagaVersion
from saga_orchestration.domain.step_attempt import StepAttempt

if TYPE_CHECKING:
    from saga_orchestration.domain.saga_key import SagaKey
    from saga_orchestration.domain.saga_payload import SagaPayload
    from saga_orchestration.domain.step import StepDefinition, StepRegistry
    from saga_orchestration.domain.step_name import StepName


class Saga(AggregateRoot[SagaId]):
    """Maszyna stanów sagi. Każda mutacja: guard -> mutacja (+bump wersji) -> event."""

    __slots__ = (
        "_key",
        "_payload",
        "_status",
        "_steps",
        "_current_step",
        "_completed_steps",
        "_failed_steps",
        "_compensation_stack",
        "_compensation_cursor",
        "_attempts",
        "_version",
        "_created_at",
        "_updated_at",
        "_completed_at",
        "_failed_at",
        "_compensated_at",
    )

    def __init__(
        self, *, saga_id: SagaId, key: SagaKey, payload: SagaPayload, steps: StepRegistry
    ) -> None:
        super().__init__(saga_id)
        self._key = key
        self._payload = payload
        self._status = SagaStatus.CREATED
        self._steps = steps
        self._current_step: StepName | None = None
        self._completed_steps: tuple[StepName, ...] = ()
        self._failed_steps: tuple[StepName, ...] = ()
        self._compensation_stack: tuple[StepName, ...] = ()
        self._compensation_cursor = 0
        self._attempts: tuple[StepAttempt, ...] = ()
        self._version = SagaVersion.initial()
        now = datetime.now().astimezone()
        self._created_at = now
        self._updated_at = now
        self._completed_at: datetime | None = None
        self._failed_at: datetime | None = None
        self._compensated_at: datetime | None = None

    @classmethod
    def start(
        cls,
        *,
        saga_id: SagaId,
        key: SagaKey,
        payload: SagaPayload,
        steps: StepRegistry,
        now: datetime,
    ) -> Self:
        saga = cls(saga_id=saga_id, key=key, payload=payload, steps=steps)
        first = steps.steps[0]
        saga._status = SagaStatus.RUNNING
        saga._current_step = first.name
        saga._attempts = (StepAttempt(step=first.name, attempt=1),)
        saga._created_at = now
        saga._updated_at = now
        saga.append_event(SagaStartedEvent.now(saga_id=saga_id, key=key, at=now))
        saga.append_event(
            StepDispatchedEvent.now(
                saga_id=saga_id, attempt=StepAttempt(step=first.name, attempt=1), at=now
            )
        )
        return saga

    @classmethod
    def restore(
        cls,
        *,
        saga_id: SagaId,
        key: SagaKey,
        payload: SagaPayload,
        steps: StepRegistry,
        status: SagaStatus,
        current_step: StepName | None,
        completed: tuple[StepName, ...],
        failed: tuple[StepName, ...],
        compensation_stack: tuple[StepName, ...],
        compensation_cursor: int,
        attempts: tuple[StepAttempt, ...],
        version: SagaVersion,
        created_at: datetime,
        updated_at: datetime,
        completed_at: datetime | None,
        failed_at: datetime | None,
        compensated_at: datetime | None,
    ) -> Self:
        saga = cls(saga_id=saga_id, key=key, payload=payload, steps=steps)
        saga._status = status
        saga._current_step = current_step
        saga._completed_steps = completed
        saga._failed_steps = failed
        saga._compensation_stack = compensation_stack
        saga._compensation_cursor = compensation_cursor
        saga._attempts = attempts
        saga._version = version
        saga._created_at = created_at
        saga._updated_at = updated_at
        saga._completed_at = completed_at
        saga._failed_at = failed_at
        saga._compensated_at = compensated_at
        return saga

    @property
    def key(self) -> SagaKey:
        return self._key

    @property
    def payload(self) -> SagaPayload:
        return self._payload

    @property
    def status(self) -> SagaStatus:
        return self._status

    @property
    def steps(self) -> StepRegistry:
        return self._steps

    @property
    def current_step(self) -> StepName | None:
        return self._current_step

    @property
    def completed_steps(self) -> tuple[StepName, ...]:
        return self._completed_steps

    @property
    def failed_steps(self) -> tuple[StepName, ...]:
        return self._failed_steps

    @property
    def compensation_stack(self) -> tuple[StepName, ...]:
        return self._compensation_stack

    @property
    def compensation_cursor(self) -> int:
        return self._compensation_cursor

    @property
    def attempts(self) -> tuple[StepAttempt, ...]:
        return self._attempts

    @property
    def version(self) -> SagaVersion:
        return self._version

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def completed_at(self) -> datetime | None:
        return self._completed_at

    @property
    def failed_at(self) -> datetime | None:
        return self._failed_at

    @property
    def compensated_at(self) -> datetime | None:
        return self._compensated_at

    @property
    def is_terminal(self) -> bool:
        return self._status in (
            SagaStatus.COMPLETED,
            SagaStatus.FAILED,
            SagaStatus.COMPENSATED,
        )

    def attempt_of(self, step: StepName) -> int:
        for record in self._attempts:
            if record.step == step:
                return record.attempt
        return 0

    def on_step_succeeded(self, step: StepName, attempt: int, *, now: datetime) -> StepName | None:
        if self._status is not SagaStatus.RUNNING:
            raise SagaGuardError(f"succeeded tylko z RUNNING, jest {self._status.value}")
        if self._current_step != step:
            raise SagaGuardError(f"oczekiwano {self._current_step}, przyszło {step}")
        if self.attempt_of(step) != attempt:
            raise SagaGuardError(f"stale attempt {attempt} dla {step.value}")
        self._completed_steps = (*self._completed_steps, step)
        self._touch(now)
        self.append_event(
            StepSucceededEvent.now(
                saga_id=self.id, attempt=StepAttempt(step=step, attempt=attempt), at=now
            )
        )
        nxt = self._next_after(step)
        if nxt is None:
            self._status = SagaStatus.COMPLETED
            self._current_step = None
            self._completed_at = now
            self._touch(now)
            self.append_event(SagaCompletedEvent.now(saga_id=self.id, at=now))
            return None
        self._current_step = nxt.name
        self._attempts = (
            *self._attempts_for_others(nxt.name),
            StepAttempt(step=nxt.name, attempt=1),
        )
        self._touch(now)
        self.append_event(
            StepDispatchedEvent.now(
                saga_id=self.id, attempt=StepAttempt(step=nxt.name, attempt=1), at=now
            )
        )
        return nxt.name

    def on_step_failed(
        self, step: StepName, attempt: int, *, now: datetime, timed_out: bool = False
    ) -> StepName | None:
        """Zwraca krok do dispatchu (retry ten sam / kompensata) albo None (terminal)."""
        if self._status is not SagaStatus.RUNNING:
            raise SagaGuardError(f"failed tylko z RUNNING, jest {self._status.value}")
        if self._current_step != step:
            raise SagaGuardError(f"oczekiwano {self._current_step}, przyszło {step}")
        if self.attempt_of(step) != attempt:
            raise SagaGuardError(f"stale attempt {attempt} dla {step.value}")
        definition = self._steps.by_name(step)
        self._failed_steps = (*self._failed_steps, step)
        self._touch(now)
        self.append_event(
            StepFailedEvent.now(
                saga_id=self.id, attempt=StepAttempt(step=step, attempt=attempt), at=now
            )
        )
        if timed_out:
            self.append_event(
                SagaTimedOutEvent.now(
                    saga_id=self.id, attempt=StepAttempt(step=step, attempt=attempt), at=now
                )
            )
        if attempt < definition.max_attempts:
            return step
        stack = self._build_compensation_stack(step)
        if not stack:
            self._status = SagaStatus.FAILED
            self._current_step = None
            self._failed_at = now
            self._touch(now)
            self.append_event(SagaFailedEvent.now(saga_id=self.id, at=now))
            return None
        self._compensation_stack = stack
        self._compensation_cursor = 0
        first_compensation = stack[0]
        self._status = SagaStatus.COMPENSATING
        self._current_step = first_compensation
        self._attempts = (
            *self._attempts_for_others(first_compensation),
            StepAttempt(step=first_compensation, attempt=1),
        )
        self._touch(now)
        self.append_event(
            CompensationStartedEvent.now(saga_id=self.id, compensation=first_compensation, at=now)
        )
        self.append_event(
            StepDispatchedEvent.now(
                saga_id=self.id,
                attempt=StepAttempt(step=first_compensation, attempt=1),
                at=now,
            )
        )
        return first_compensation

    def on_retry_dispatched(self, step: StepName, attempt: int, *, now: datetime) -> None:
        """Worker odpala odroczony retry: ewidencja próby + event, w tej samej transakcji."""
        if self._status is not SagaStatus.RUNNING:
            raise SagaGuardError(f"retry tylko z RUNNING, jest {self._status.value}")
        if self._current_step != step:
            raise SagaGuardError(f"oczekiwano {self._current_step}, przyszło {step}")
        if self.attempt_of(step) != attempt - 1:
            raise SagaGuardError(f"retry attempt {attempt} po {self.attempt_of(step)}")
        self._attempts = (*self._attempts_for_others(step), StepAttempt(step=step, attempt=attempt))
        self._touch(now)
        self.append_event(
            StepDispatchedEvent.now(
                saga_id=self.id, attempt=StepAttempt(step=step, attempt=attempt), at=now
            )
        )

    def on_compensation_done(
        self, step: StepName, attempt: int, *, now: datetime
    ) -> StepName | None:
        if self._status is not SagaStatus.COMPENSATING:
            raise SagaGuardError(
                f"compensation_done tylko z COMPENSATING, jest {self._status.value}"
            )
        if self._compensation_cursor >= len(self._compensation_stack):
            raise SagaGuardError("pusty stos kompensat")
        expected = self._compensation_stack[self._compensation_cursor]
        if expected != step:
            raise SagaGuardError(f"oczekiwano kompensaty {expected.value}, przyszło {step.value}")
        if self.attempt_of(step) != attempt:
            raise SagaGuardError(f"stale attempt {attempt} dla kompensaty {step.value}")
        self._compensation_cursor += 1
        self._touch(now)
        self.append_event(CompensationDoneEvent.now(saga_id=self.id, compensation=step, at=now))
        if self._compensation_cursor >= len(self._compensation_stack):
            self._status = SagaStatus.COMPENSATED
            self._current_step = None
            self._compensated_at = now
            self._touch(now)
            self.append_event(SagaCompensatedEvent.now(saga_id=self.id, at=now))
            return None
        nxt = self._compensation_stack[self._compensation_cursor]
        self._current_step = nxt
        self._attempts = (*self._attempts_for_others(nxt), StepAttempt(step=nxt, attempt=1))
        self._touch(now)
        self.append_event(
            StepDispatchedEvent.now(
                saga_id=self.id, attempt=StepAttempt(step=nxt, attempt=1), at=now
            )
        )
        return nxt

    def on_compensation_failed(self, step: StepName, attempt: int, *, now: datetime) -> None:
        """Nieudana kompensata: status bez zmian, kursor stoi, handler odracza retry."""
        if self._status is not SagaStatus.COMPENSATING:
            raise SagaGuardError(
                f"compensation_failed tylko z COMPENSATING, jest {self._status.value}"
            )
        if self._compensation_cursor >= len(self._compensation_stack):
            raise SagaGuardError("pusty stos kompensat")
        expected = self._compensation_stack[self._compensation_cursor]
        if expected != step:
            raise SagaGuardError(f"oczekiwano kompensaty {expected.value}, przyszło {step.value}")
        if self.attempt_of(step) != attempt:
            raise SagaGuardError(f"stale attempt {attempt} dla kompensaty {step.value}")
        self._touch(now)
        self.append_event(
            StepFailedEvent.now(
                saga_id=self.id, attempt=StepAttempt(step=step, attempt=attempt), at=now
            )
        )

    def on_compensation_redispatched(self, step: StepName, attempt: int, *, now: datetime) -> None:
        if self._status is not SagaStatus.COMPENSATING:
            raise SagaGuardError(
                f"retry kompensaty tylko z COMPENSATING, jest {self._status.value}"
            )
        if self._compensation_cursor >= len(self._compensation_stack):
            raise SagaGuardError("pusty stos kompensat")
        expected = self._compensation_stack[self._compensation_cursor]
        if expected != step:
            raise SagaGuardError(f"oczekiwano kompensaty {expected.value}, przyszło {step.value}")
        if self.attempt_of(step) != attempt - 1:
            raise SagaGuardError(f"retry attempt {attempt} po {self.attempt_of(step)}")
        self._attempts = (*self._attempts_for_others(step), StepAttempt(step=step, attempt=attempt))
        self._touch(now)
        self.append_event(
            StepDispatchedEvent.now(
                saga_id=self.id, attempt=StepAttempt(step=step, attempt=attempt), at=now
            )
        )

    def _touch(self, now: datetime) -> None:
        self._version = self._version.next()
        self._updated_at = now

    def _attempts_for_others(self, step: StepName) -> tuple[StepAttempt, ...]:
        return tuple(record for record in self._attempts if record.step != step)

    def _next_after(self, step: StepName) -> StepDefinition | None:
        names = [definition.name for definition in self._steps.steps]
        position = names.index(step)
        if position + 1 >= len(self._steps.steps):
            return None
        return self._steps.steps[position + 1]

    def _build_compensation_stack(self, failed: StepName) -> tuple[StepName, ...]:
        """Stos: najpierw sprzątanie NIEUDANEGO kroku, potem odwrócone ukończone.

        Nieudana próba też zostawia częściowe efekty (jak provision pilota) —
        jej własna kompensata idzie na czoło (parzystość z pilotem).
        """
        stack: list[StepName] = []
        own = self._steps.by_name(failed).compensation_step
        if own is not None:
            stack.append(own)
        for done in reversed(self._completed_steps):
            compensation = self._steps.by_name(done).compensation_step
            if compensation is not None and compensation not in stack:
                stack.append(compensation)
        return tuple(stack)
