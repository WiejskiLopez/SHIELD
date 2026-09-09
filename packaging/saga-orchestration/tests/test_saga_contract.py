from __future__ import annotations

from datetime import timedelta

import pytest
from saga_orchestration.application.advance_saga_handler import AdvanceSagaCommand
from saga_orchestration.application.start_saga_handler import StartSagaCommand
from saga_orchestration.application.timeout_saga_handler import TimeoutSagaCommand
from saga_orchestration.domain.errors import (
    SagaDomainError,
    SagaGuardError,
    SagaVersionConflictError,
)
from saga_orchestration.domain.processed_delivery import DeliveryId
from saga_orchestration.domain.saga import Saga
from saga_orchestration.domain.saga_id import SagaId
from saga_orchestration.domain.saga_key import SagaKey
from saga_orchestration.domain.saga_payload import SagaPayload
from saga_orchestration.domain.saga_status import SagaStatus
from saga_orchestration.domain.step_name import StepName
from saga_orchestration.domain.timeout_kind import TimeoutKind
from saga_test_kit import (
    NOTIFY,
    PROVISION,
    RELEASE,
    STEP_A,
    STEP_B,
    UNDO_A,
    UNDO_B,
    InMemoryHarness,
    claim_due_rows,
    three_step_registry,
    two_step_registry,
)

SAGA_TYPE = "provision_case"


def make_key(name: str = "project-1") -> SagaKey:
    return SagaKey(saga_type=SAGA_TYPE, business_key=name)


def start_command(key: SagaKey) -> StartSagaCommand:
    return StartSagaCommand(
        key=key,
        payload=SagaPayload({"business_key": key.business_key, "marker": "m-1"}),
        steps=two_step_registry(),
        correlation_id="corr-1",
        causation_id=None,
    )


def advance_command(
    key: SagaKey,
    delivery: str,
    step: StepName,
    attempt: int,
    succeeded: bool,
    *,
    is_compensation: bool = False,
) -> AdvanceSagaCommand:
    return AdvanceSagaCommand(
        key=key,
        delivery_id=DeliveryId(delivery),
        step=step,
        attempt=attempt,
        succeeded=succeeded,
        is_compensation=is_compensation,
        correlation_id="corr-1",
        causation_id=None,
    )


async def load(harness: InMemoryHarness, key: SagaKey) -> Saga:
    async with harness.factory() as uow:
        saga = await uow.sagas.get_by_key(key)
    assert saga is not None
    return saga


@pytest.mark.asyncio
async def test_start_stores_saga_dispatches_first_step_and_schedules_deadline() -> None:
    harness = InMemoryHarness({SAGA_TYPE: two_step_registry()})
    start, _, _ = harness.handlers()
    key = make_key()

    saga_id = await start.handle(start_command(key))

    saga = await load(harness, key)
    assert saga.id == saga_id
    assert saga.status is SagaStatus.RUNNING
    assert saga.current_step == PROVISION
    assert saga.attempt_of(PROVISION) == 1
    assert [row.command_id for row in harness.store.outbox] == [
        f"{saga_id.value}:provision_workspace:1"
    ]
    assert harness.store.outbox[0].payload["marker"] == "m-1"
    assert len(harness.store.timeouts) == 1
    timeout = next(iter(harness.store.timeouts.values()))
    assert timeout.kind is TimeoutKind.RESULT_DEADLINE
    assert timeout.attempt == 1

    fresh = Saga.start(
        saga_id=SagaId("emissions"),
        key=make_key("emissions"),
        payload=SagaPayload.empty(),
        steps=two_step_registry(),
        now=harness.clock.now(),
    )
    assert [type(event).__name__ for event in fresh.pull_events()] == [
        "SagaStartedEvent",
        "StepDispatchedEvent",
    ]
    assert fresh.pull_events() == []


@pytest.mark.asyncio
async def test_start_is_idempotent_on_same_key() -> None:
    harness = InMemoryHarness({SAGA_TYPE: two_step_registry()})
    start, _, _ = harness.handlers()
    key = make_key()

    first = await start.handle(start_command(key))
    second = await start.handle(start_command(key))

    assert first == second
    assert len(harness.store.sagas) == 1
    assert len(harness.store.outbox) == 1


@pytest.mark.asyncio
async def test_advance_success_moves_to_next_and_cancels_deadline() -> None:
    harness = InMemoryHarness({SAGA_TYPE: two_step_registry()})
    start, advance, _ = harness.handlers()
    key = make_key()
    await start.handle(start_command(key))

    await advance.handle(advance_command(key, "evt-1", PROVISION, 1, True))

    saga = await load(harness, key)
    assert saga.status is SagaStatus.RUNNING
    assert saga.current_step == NOTIFY
    assert saga.completed_steps == (PROVISION,)
    assert [row.command_id for row in harness.store.outbox] == [
        f"{saga.id.value}:provision_workspace:1",
        f"{saga.id.value}:notify_owner:1",
    ]
    assert all(
        stored.status.value != "pending" or stored.step != PROVISION
        for stored in harness.store.timeouts.values()
    )


@pytest.mark.asyncio
async def test_duplicate_delivery_is_noop() -> None:
    harness = InMemoryHarness({SAGA_TYPE: two_step_registry()})
    start, advance, _ = harness.handlers()
    key = make_key()
    await start.handle(start_command(key))

    await advance.handle(advance_command(key, "evt-1", PROVISION, 1, True))
    before = await load(harness, key)
    await advance.handle(advance_command(key, "evt-1", PROVISION, 1, True))
    after = await load(harness, key)

    assert before.version == after.version
    assert len(harness.store.outbox) == 2
    assert len(harness.store.deliveries) == 1


@pytest.mark.asyncio
async def test_stale_attempt_is_noop() -> None:
    harness = InMemoryHarness({SAGA_TYPE: two_step_registry()})
    start, advance, _ = harness.handlers()
    key = make_key()
    await start.handle(start_command(key))
    await advance.handle(advance_command(key, "evt-1", PROVISION, 1, True))

    await advance.handle(advance_command(key, "evt-2", PROVISION, 1, True))

    saga = await load(harness, key)
    assert saga.current_step == NOTIFY
    assert len(harness.store.outbox) == 2
    assert len(harness.store.deliveries) == 1


@pytest.mark.asyncio
async def test_missing_saga_is_noop() -> None:
    harness = InMemoryHarness({SAGA_TYPE: two_step_registry()})
    _, advance, _ = harness.handlers()

    await advance.handle(advance_command(make_key("ghost"), "evt-9", PROVISION, 1, True))

    assert harness.store.sagas == {}
    assert harness.store.outbox == []


@pytest.mark.asyncio
async def test_retry_then_compensate() -> None:
    registry = three_step_registry(max_attempts_b=2)
    harness = InMemoryHarness({"three": registry})
    start, advance, timeout = harness.handlers()
    key = SagaKey(saga_type="three", business_key="case-1")
    await start.handle(
        StartSagaCommand(
            key=key,
            payload=SagaPayload.empty(),
            steps=registry,
            correlation_id="corr-1",
            causation_id=None,
        )
    )
    await advance.handle(advance_command(key, "a-ok", STEP_A, 1, True))
    await advance.handle(advance_command(key, "b-fail-1", STEP_B, 1, False))

    saga = await load(harness, key)
    assert saga.status is SagaStatus.RUNNING
    assert saga.current_step == STEP_B
    assert [row.command_id for row in harness.store.outbox] == [
        f"{saga.id.value}:step_a:1",
        f"{saga.id.value}:step_b:1",
    ]
    claimed = await claim_due_rows(harness)
    assert len(claimed) == 1
    assert claimed[0].kind is TimeoutKind.RETRY_DELAY
    assert claimed[0].attempt == 2

    await timeout.handle(
        TimeoutSagaCommand(
            timeout_id=claimed[0].timeout_id,
            key=key,
            step=STEP_B,
            attempt=2,
            kind=TimeoutKind.RETRY_DELAY,
            correlation_id="corr-1",
            causation_id=None,
        )
    )

    saga = await load(harness, key)
    assert saga.attempt_of(STEP_B) == 2
    assert [row.command_id for row in harness.store.outbox][-1] == (f"{saga.id.value}:step_b:2")

    await advance.handle(advance_command(key, "b-fail-2", STEP_B, 2, False))

    saga = await load(harness, key)
    assert saga.status is SagaStatus.COMPENSATING
    assert saga.compensation_stack == (UNDO_B, UNDO_A)
    assert saga.current_step == UNDO_B
    assert [row.command_id for row in harness.store.outbox][-1] == (f"{saga.id.value}:undo_b:1")


@pytest.mark.asyncio
async def test_compensation_failure_schedules_retry_then_completes() -> None:
    harness = InMemoryHarness({SAGA_TYPE: two_step_registry(max_attempts_provision=1)})
    start, advance, timeout = harness.handlers()
    key = make_key()
    await start.handle(start_command(key))
    await advance.handle(advance_command(key, "prov-ok", PROVISION, 1, True))
    await advance.handle(advance_command(key, "not-fail", NOTIFY, 1, False))

    saga = await load(harness, key)
    assert saga.status is SagaStatus.COMPENSATING
    assert saga.compensation_stack == (RELEASE,)
    assert saga.current_step == RELEASE

    await advance.handle(
        advance_command(key, "comp-fail-1", RELEASE, 1, False, is_compensation=True)
    )

    saga = await load(harness, key)
    assert saga.status is SagaStatus.COMPENSATING
    assert saga.compensation_cursor == 0
    claimed = await claim_due_rows(harness)
    assert len(claimed) == 1
    assert claimed[0].kind is TimeoutKind.RETRY_DELAY

    await timeout.handle(
        TimeoutSagaCommand(
            timeout_id=claimed[0].timeout_id,
            key=key,
            step=RELEASE,
            attempt=2,
            kind=TimeoutKind.RETRY_DELAY,
            correlation_id="corr-1",
            causation_id=None,
        )
    )
    await advance.handle(advance_command(key, "comp-ok-2", RELEASE, 2, True, is_compensation=True))

    saga = await load(harness, key)
    assert saga.status is SagaStatus.COMPENSATED
    assert [type(event).__name__ for event in saga.pull_events()] == []


@pytest.mark.asyncio
async def test_multi_step_compensation_resumes_from_cursor() -> None:
    harness = InMemoryHarness({"three": three_step_registry()})
    start, advance, _ = harness.handlers()
    key = SagaKey(saga_type="three", business_key="case-1")
    await start.handle(
        StartSagaCommand(
            key=key,
            payload=SagaPayload.empty(),
            steps=three_step_registry(),
            correlation_id="corr-1",
            causation_id=None,
        )
    )
    from saga_orchestration.domain.step_name import StepName as SN

    await advance.handle(advance_command(key, "a-ok", SN("step_a"), 1, True))
    await advance.handle(advance_command(key, "b-ok", SN("step_b"), 1, True))
    await advance.handle(advance_command(key, "c-fail", SN("step_c"), 1, False))

    saga = await load(harness, key)
    assert saga.status is SagaStatus.COMPENSATING
    assert saga.compensation_stack == (SN("undo_b"), SN("undo_a"))
    assert saga.compensation_cursor == 0

    await advance.handle(advance_command(key, "ub-ok", SN("undo_b"), 1, True, is_compensation=True))
    saga = await load(harness, key)
    assert saga.compensation_cursor == 1
    assert saga.current_step == SN("undo_a")

    async with harness.factory() as uow:
        restarted = await uow.sagas.get_by_key(key)
    assert restarted is not None
    assert restarted.compensation_cursor == 1
    assert restarted.pull_events() == []

    await advance.handle(advance_command(key, "ua-ok", SN("undo_a"), 1, True, is_compensation=True))
    saga = await load(harness, key)
    assert saga.status is SagaStatus.COMPENSATED


@pytest.mark.asyncio
async def test_restore_emits_nothing_and_guards_raise() -> None:
    harness = InMemoryHarness({SAGA_TYPE: two_step_registry()})
    start, _, _ = harness.handlers()
    key = make_key()
    await start.handle(start_command(key))

    saga = await load(harness, key)
    assert saga.pull_events() == []

    fresh = Saga(
        saga_id=SagaId("fresh"),
        key=key,
        payload=SagaPayload.empty(),
        steps=two_step_registry(),
    )
    with pytest.raises(SagaGuardError):
        fresh.on_step_succeeded(PROVISION, 1, now=harness.clock.now())
    with pytest.raises(SagaDomainError):
        StepName("")


@pytest.mark.asyncio
async def test_atomic_rollback_when_outbox_fails() -> None:
    harness = InMemoryHarness({SAGA_TYPE: two_step_registry()})
    start, _, _ = harness.handlers()
    key = make_key()

    class ExplodingOutbox(list):  # type: ignore[type-arg]
        def append(self, item: object) -> None:
            raise RuntimeError("outbox down")

    harness.store.outbox = ExplodingOutbox()  # type: ignore[assignment]
    with pytest.raises(RuntimeError, match="outbox down"):
        await start.handle(start_command(key))

    assert harness.store.sagas == {}
    assert harness.store.keys == {}


@pytest.mark.asyncio
async def test_version_conflict_on_concurrent_store() -> None:
    harness = InMemoryHarness({SAGA_TYPE: two_step_registry()})
    start, advance, _ = harness.handlers()
    key = make_key()
    await start.handle(start_command(key))

    async with harness.factory() as first_uow:
        first = await first_uow.sagas.get_by_key(key)
        assert first is not None
        first_persisted = first.version
        async with harness.factory() as second_uow:
            second = await second_uow.sagas.get_by_key(key)
            assert second is not None
            second_persisted = second.version
            second.on_step_succeeded(PROVISION, 1, now=harness.clock.now())
            await second_uow.sagas.store(second, persisted_version=second_persisted)
            first.on_step_succeeded(PROVISION, 1, now=harness.clock.now())
            with pytest.raises(SagaVersionConflictError):
                await first_uow.sagas.store(first, persisted_version=first_persisted)


@pytest.mark.asyncio
async def test_deadline_fires_as_failure_with_timeout_event() -> None:
    harness = InMemoryHarness({SAGA_TYPE: two_step_registry()})
    start, _, _ = harness.handlers()
    key = make_key()
    await start.handle(start_command(key))
    harness.clock.advance(timedelta(minutes=6))

    worker = harness.worker()
    processed = await worker.run_once()

    assert processed == 1
    saga = await load(harness, key)
    assert saga.status is SagaStatus.RUNNING
    assert saga.attempt_of(PROVISION) == 1
    pending = [
        stored for stored in harness.store.timeouts.values() if stored.status.value == "pending"
    ]
    assert len(pending) == 1
    assert pending[0].kind is TimeoutKind.RETRY_DELAY
    journal = harness.store.deliveries
    assert len(journal) == 1
    entry = next(iter(journal.values()))
    assert entry.succeeded is False
    assert entry.delivery_id.value.startswith("timeout:")


@pytest.mark.asyncio
async def test_failed_first_step_compensates_itself_pilot_parity() -> None:
    """Nawet bez ukończonych kroków: kompensata nieudanego kroku sprząta częściowe efekty."""
    harness = InMemoryHarness({SAGA_TYPE: two_step_registry(max_attempts_provision=1)})
    start, advance, _ = harness.handlers()
    key = make_key()
    await start.handle(start_command(key))
    await advance.handle(advance_command(key, "fail-1", PROVISION, 1, False))

    saga = await load(harness, key)
    assert saga.status is SagaStatus.COMPENSATING
    assert saga.compensation_stack == (RELEASE,)
    assert saga.current_step == RELEASE

    await advance.handle(advance_command(key, "rel-ok", RELEASE, 1, True, is_compensation=True))
    saga = await load(harness, key)
    assert saga.status is SagaStatus.COMPENSATED


@pytest.mark.asyncio
async def test_full_run_completes_and_terminal_results_are_noop() -> None:
    harness = InMemoryHarness({SAGA_TYPE: two_step_registry()})
    start, advance, _ = harness.handlers()
    key = make_key()
    await start.handle(start_command(key))
    await advance.handle(advance_command(key, "evt-1", PROVISION, 1, True))
    await advance.handle(advance_command(key, "evt-2", NOTIFY, 1, True))

    saga = await load(harness, key)
    assert saga.status is SagaStatus.COMPLETED
    assert saga.completed_steps == (PROVISION, NOTIFY)
    assert len(harness.store.outbox) == 2
    assert not [
        stored for stored in harness.store.timeouts.values() if stored.status.value == "pending"
    ]

    await advance.handle(advance_command(key, "evt-3", NOTIFY, 1, True))
    resurrected = await load(harness, key)
    assert resurrected.status is SagaStatus.COMPLETED
    assert len(harness.store.outbox) == 2
    assert len(harness.store.deliveries) == 2


@pytest.mark.asyncio
async def test_claim_lease_recovery_processes_once() -> None:
    harness = InMemoryHarness({SAGA_TYPE: two_step_registry()})
    start, _, _ = harness.handlers()
    key = make_key()
    await start.handle(start_command(key))
    harness.clock.advance(timedelta(minutes=6))

    harness.worker(owner="worker-a")
    worker_b = harness.worker(owner="worker-b")

    async with harness.factory() as uow:
        claimed = await uow.timeouts.claim_due(
            owner="worker-a",
            now=harness.clock.now(),
            lease_until=harness.clock.now() + timedelta(minutes=1),
            limit=10,
        )
    assert len(claimed) == 1

    harness.clock.advance(timedelta(minutes=2))
    processed = await worker_b.run_once()
    assert processed == 1

    saga = await load(harness, key)
    assert [row.command_id for row in harness.store.outbox] == [
        f"{saga.id.value}:provision_workspace:1"
    ]
    pending_retry = [
        stored for stored in harness.store.timeouts.values() if stored.status.value == "pending"
    ]
    assert len(pending_retry) == 1
