"""Druga saga jako dowód generalizacji: pełna pętla na klockach schedulingu.

Real wiring (install_saga, CommandInboxProcessor, EventInboxProcessor, uczestnicy
na outbox, worker timeoutów) against SQLite. Transport jest symulowany: wiersze
outbox są klonowane do inbox z dedupem jak konsument (odpowiednik relay + broker
+ consumer). Brak brokera w teście. Kopia wzorca z project_service (SAGA.MD Krok 7).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import pytest
from saga_orchestration.bootstrap.install import install_saga
from saga_orchestration.domain.saga_key import SagaKey
from saga_orchestration.domain.saga_status import SagaStatus
from saga_orchestration.domain.step_name import StepName
from saga_orchestration.infrastructure.in_memory.fake_clock import FakeClock, FakeIds
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine

from shell.platform.application.bus.command_bus import CommandBus
from shell.platform.application.bus.command_bus_publisher import CommandBusPublisher
from shell.platform.application.bus.event_bus import EventBus
from shell.platform.infrastructure.messaging.command.command_inbox_processor import (
    CommandInboxProcessor,
)
from shell.platform.infrastructure.messaging.event.event_inbox_processor import (
    EventInboxProcessor,
)
from shell.platform.infrastructure.messaging.inbox.envelope_validator import (
    envelope_policy_from_catalog,
)
from shell.platform.infrastructure.persistence.sql import (
    build_session_factory,
    dispose_session_factory,
)
from shell.platform.infrastructure.serialization.upcaster import PayloadUpcaster
from shell.scheduling_service.application.scheduling.scheduler_provision.command_handlers.provision_schedule_handler import (
    ProvisionScheduleHandler,
)
from shell.scheduling_service.application.scheduling.scheduler_provision.command_handlers.release_schedule_handler import (
    ReleaseScheduleHandler,
)
from shell.scheduling_service.application.scheduling.scheduler_provision.commands.provision_schedule_command import (
    ProvisionScheduleCommand,
)
from shell.scheduling_service.application.scheduling.scheduler_provision.commands.release_schedule_command import (
    ReleaseScheduleCommand,
)
from shell.scheduling_service.application.scheduling.scheduler_provision.commands.start_scheduler_provision_command import (
    StartSchedulerProvisionCommand,
)
from shell.scheduling_service.application.scheduling.scheduler_provision.integration_events.schedule_provision_failed_integration_event import (
    ScheduleProvisionFailedIntegrationEvent,
)
from shell.scheduling_service.application.scheduling.scheduler_provision.integration_events.schedule_provisioned_integration_event import (
    ScheduleProvisionedIntegrationEvent,
)
from shell.scheduling_service.application.scheduling.scheduler_provision.integration_events.schedule_released_integration_event import (
    ScheduleReleasedIntegrationEvent,
)
from shell.scheduling_service.bootstrap.scheduling.command_contracts import (
    SCHEDULING_COMMAND_CONTRACTS,
    build_scheduling_command_registry,
)
from shell.scheduling_service.bootstrap.scheduling.contract_catalog import (
    SCHEDULING_CONTRACT_CATALOG,
)
from shell.scheduling_service.bootstrap.scheduling.event_registry import (
    build_scheduling_event_registry,
)
from shell.scheduling_service.infrastructure.scheduling.persistence.sql.models.base import (
    PERSISTENCE_DELIVERY_MODELS,
    SAGA_MODELS,
)
from shell.scheduling_service.infrastructure.scheduling.saga.saga_result_writer import (
    SqlScheduleResultWriter,
)
from shell.scheduling_service.infrastructure.scheduling.saga.saga_wiring import (
    build_scheduling_saga_unit_of_work_factory,
)
from shell.scheduling_service.process.scheduling.scheduler_provision.handlers.provision_result_bridge_handler import (
    ProvisionResultBridgeHandler,
)
from shell.scheduling_service.process.scheduling.scheduler_provision.handlers.release_result_bridge_handler import (
    ReleaseResultBridgeHandler,
)
from shell.scheduling_service.process.scheduling.scheduler_provision.handlers.start_saga_bridge_handler import (
    StartSchedulerProvisionBridgeHandler,
)
from shell.scheduling_service.process.scheduling.scheduler_provision.saga_definition import (
    SAGA_TYPE,
    SCHEDULER_PROVISION_STEPS,
)
from shell.scheduling_service.process.scheduling.scheduler_provision.saga_dispatch import (
    SchedulerProvisionDispatchResolver,
)

_COMMAND_OUTBOX: Any = PERSISTENCE_DELIVERY_MODELS.commands.outbox
_COMMAND_INBOX: Any = PERSISTENCE_DELIVERY_MODELS.commands.inbox
_EVENT_OUTBOX: Any = PERSISTENCE_DELIVERY_MODELS.events.outbox
_EVENT_INBOX: Any = PERSISTENCE_DELIVERY_MODELS.events.inbox
_SAGA_TIMEOUT_MODEL: Any = SAGA_MODELS.timeout

if TYPE_CHECKING:
    from pathlib import Path

    from saga_orchestration.domain.saga import Saga
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def _now() -> datetime:
    return datetime.now(tz=UTC)


class SagaSchedulingWorld:
    """Cały serwis w teście: bazy, busy, procesory, wiring install_saga, mosty."""

    def __init__(self, db_path: Path) -> None:
        from shell.scheduling_service.infrastructure.scheduling.persistence.sql.models.base import (
            SchedulingSqlAlchemyModelBase,
        )

        self.url = f"sqlite+aiosqlite:///{db_path}"
        self.metadata = SchedulingSqlAlchemyModelBase.metadata
        self.session_factory = build_session_factory(self.url)
        self.clock = FakeClock()
        self.ids = FakeIds(prefix="saga")
        self.command_bus = CommandBus()
        self.event_bus = EventBus()
        self.command_registry = build_scheduling_command_registry()
        self.event_registry = build_scheduling_event_registry()
        self.result_writer = SqlScheduleResultWriter(PERSISTENCE_DELIVERY_MODELS.events)
        self.resolver = SchedulerProvisionDispatchResolver()
        self.wiring = install_saga(
            uow_factory=build_scheduling_saga_unit_of_work_factory(
                session_factory=lambda: self.session_factory(),
                models=SAGA_MODELS,
                commands_models=PERSISTENCE_DELIVERY_MODELS.commands,
                contracts=SCHEDULING_COMMAND_CONTRACTS,
                registries={SAGA_TYPE: SCHEDULER_PROVISION_STEPS},
            ),
            dispatch_resolver=self.resolver,
            clock=self.clock,
            ids=self.ids,
            source_service="scheduling",
            owner="scheduler-test-timeout",
        )
        self._wire_buses()
        self._build_processors()

    def _wire_buses(self) -> None:
        self.command_bus.register(
            StartSchedulerProvisionCommand,
            lambda: StartSchedulerProvisionBridgeHandler(self.wiring.start_handler),
        )
        self.command_bus.register(
            ProvisionScheduleCommand,
            lambda: ProvisionScheduleHandler(self.result_writer),
        )
        self.command_bus.register(
            ReleaseScheduleCommand,
            lambda: ReleaseScheduleHandler(self.result_writer),
        )
        self.event_bus.subscribe(
            ScheduleProvisionedIntegrationEvent,
            lambda: ProvisionResultBridgeHandler(self.wiring.advance_handler),
        )
        self.event_bus.subscribe(
            ScheduleProvisionFailedIntegrationEvent,
            lambda: ProvisionResultBridgeHandler(self.wiring.advance_handler),
        )
        self.event_bus.subscribe(
            ScheduleReleasedIntegrationEvent,
            lambda: ReleaseResultBridgeHandler(self.wiring.advance_handler),
        )

    def _build_processors(self) -> None:
        self.command_processor = CommandInboxProcessor(
            session_factory=self.session_factory,
            dispatcher=CommandBusPublisher(self.command_bus),
            models=PERSISTENCE_DELIVERY_MODELS.commands,
            registry=self.command_registry,
            worker_id="scheduler-command-processor",
            upcaster=PayloadUpcaster(),
        )
        self.event_processor = EventInboxProcessor(
            session_factory=self.session_factory,
            event_bus=self.event_bus,
            models=PERSISTENCE_DELIVERY_MODELS.events,
            registry=self.event_registry,
            worker_id="scheduler-event-processor",
            envelope_policy=envelope_policy_from_catalog(SCHEDULING_CONTRACT_CATALOG),
            upcaster=PayloadUpcaster(),
        )

    async def create_schema(self) -> None:
        engine = getattr(self.session_factory, "_shell_engine", None)
        if not isinstance(engine, AsyncEngine):
            raise RuntimeError("fabryka sesji bez silnika")
        async with engine.begin() as connection:
            await connection.run_sync(self.metadata.create_all)

    async def clone_commands_to_inbox(self) -> int:
        return await _clone_table(
            self.session_factory,
            _COMMAND_OUTBOX,
            _COMMAND_INBOX,
            "command",
        )

    async def clone_events_to_inbox(self) -> int:
        return await _clone_table(
            self.session_factory,
            _EVENT_OUTBOX,
            _EVENT_INBOX,
            "event",
        )

    async def pump_commands(self) -> None:
        await self.clone_commands_to_inbox()
        await self.command_processor.run_once()

    async def pump_events(self) -> None:
        await self.clone_events_to_inbox()
        await self.event_processor.run_once()

    async def load_saga(self, scheduler_job_id: str) -> Saga | None:
        uow = self.wiring.uow_factory()
        try:
            async with uow:
                return await uow.sagas.get_by_key(
                    SagaKey(saga_type=SAGA_TYPE, business_key=scheduler_job_id)
                )
        finally:
            await uow.close()

    async def outbox_command_ids(self) -> list[str]:
        async with self.session_factory() as session:
            rows: list[Any] = list((await session.execute(select(_COMMAND_OUTBOX))).scalars())
            return [str(row.command_id) for row in rows]

    async def inbox_command_attempts(self, command_name: str) -> list[int]:
        async with self.session_factory() as session:
            rows: list[Any] = list(
                (
                    await session.execute(
                        select(_COMMAND_INBOX).where(_COMMAND_INBOX.command_name == command_name)
                    )
                ).scalars()
            )
            return [int(row.payload["attempt"]) for row in rows]

    async def pending_saga_timeouts(self) -> int:
        async with self.session_factory() as session:
            rows: list[Any] = list(
                (
                    await session.execute(
                        select(_SAGA_TIMEOUT_MODEL).where(_SAGA_TIMEOUT_MODEL.status == "pending")
                    )
                ).scalars()
            )
            return len(rows)

    async def dispose(self) -> None:
        await dispose_session_factory(self.session_factory)

    def reboot(self) -> None:
        """Kill -9 + restart: nowa fabryka i procesory na tym samym pliku."""
        self.session_factory = build_session_factory(self.url)
        self._build_processors()


async def _clone_table(
    session_factory: async_sessionmaker[AsyncSession],
    outbox_model: Any,
    inbox_model: Any,
    kind: str,
) -> int:
    """Relay-clone z dedupem jak konsument (ON CONFLICT DO NOTHING)."""
    import uuid

    now = _now()
    cloned = 0
    async with session_factory() as session:
        rows: list[Any] = list((await session.execute(select(outbox_model))).scalars())
        for row in rows:
            if kind == "command":
                statement = (
                    pg_insert(inbox_model)
                    .values(
                        id=str(uuid.uuid4()),
                        command_id=row.command_id,
                        command_name=row.command_name,
                        source_service=row.source_service,
                        target_service=row.target_service,
                        schema_version=row.schema_version,
                        issued_at=row.issued_at,
                        payload=dict(row.payload),
                        correlation_id=row.correlation_id,
                        causation_id=row.causation_id,
                        received_at=now,
                    )
                    .on_conflict_do_nothing(index_elements=["source_service", "command_id"])
                )
            else:
                statement = (
                    pg_insert(inbox_model)
                    .values(
                        id=str(uuid.uuid4()),
                        event_id=row.event_id,
                        source_service=row.source_service,
                        integration_event_name=row.integration_event_name,
                        occurred_at=row.occurred_at,
                        aggregate_id=row.aggregate_id,
                        schema_version=row.schema_version,
                        correlation_id=row.correlation_id,
                        causation_id=row.causation_id,
                        payload=dict(row.payload),
                        received_at=now,
                    )
                    .on_conflict_do_nothing(index_elements=["source_service", "event_id"])
                )
            result = await session.execute(statement)
            cloned += int(getattr(result, "rowcount", 0) or 0)
        await session.commit()
    return cloned


@pytest.mark.asyncio
async def test_scheduler_happy_path(tmp_path: Path) -> None:
    world = SagaSchedulingWorld(tmp_path / "scheduler.db")
    await world.create_schema()

    await world.command_bus.dispatch(StartSchedulerProvisionCommand(scheduler_job_id="j1"))
    await world.pump_commands()
    await world.pump_events()

    saga = await world.load_saga("j1")
    assert saga is not None
    assert saga.status is SagaStatus.COMPLETED
    assert await world.outbox_command_ids() == [f"{saga.id.value}:provision_schedule:1"]
    await world.dispose()


@pytest.mark.asyncio
async def test_scheduler_failure_compensates_with_worker_retry(tmp_path: Path) -> None:
    world = SagaSchedulingWorld(tmp_path / "scheduler.db")
    await world.create_schema()

    await world.command_bus.dispatch(
        StartSchedulerProvisionCommand(scheduler_job_id="j2", fail=True)
    )
    await world.pump_commands()
    await world.pump_events()

    world.clock.advance(timedelta(seconds=31))
    assert await world.wiring.timeout_worker.run_once() == 1
    assert await world.inbox_command_attempts(
        "scheduling.scheduler_provision.provision_schedule"
    ) == [1]
    await world.pump_commands()
    assert await world.inbox_command_attempts(
        "scheduling.scheduler_provision.provision_schedule"
    ) == [1, 2]
    await world.pump_events()

    saga = await world.load_saga("j2")
    assert saga is not None
    assert saga.status is SagaStatus.COMPENSATING
    await world.pump_commands()
    await world.pump_events()

    saga = await world.load_saga("j2")
    assert saga is not None
    assert saga.status is SagaStatus.COMPENSATED
    assert await world.outbox_command_ids() == [
        f"{saga.id.value}:provision_schedule:1",
        f"{saga.id.value}:provision_schedule:2",
        f"{saga.id.value}:release_schedule:1",
    ]
    await world.dispose()


@pytest.mark.asyncio
async def test_scheduler_duplicate_result_is_noop(tmp_path: Path) -> None:
    world = SagaSchedulingWorld(tmp_path / "scheduler.db")
    await world.create_schema()

    await world.command_bus.dispatch(StartSchedulerProvisionCommand(scheduler_job_id="j3"))
    await world.pump_commands()
    await world.pump_events()

    duplicate = ScheduleProvisionedIntegrationEvent(
        event_id="dup-1",
        correlation_id="corr-dup",
        causation_id="cause-dup",
        occurred_at=_now(),
        aggregate_id="j3",
        schema_version=1,
        scheduler_job_id="j3",
        attempt=1,
    )
    bridge = ProvisionResultBridgeHandler(world.wiring.advance_handler)
    await bridge.handle(duplicate)
    await bridge.handle(duplicate)

    saga = await world.load_saga("j3")
    assert saga is not None
    assert saga.status is SagaStatus.COMPLETED
    assert len(await world.outbox_command_ids()) == 1
    await world.dispose()


@pytest.mark.asyncio
async def test_scheduler_restart_resumes_midflight(tmp_path: Path) -> None:
    world = SagaSchedulingWorld(tmp_path / "scheduler.db")
    await world.create_schema()

    await world.command_bus.dispatch(StartSchedulerProvisionCommand(scheduler_job_id="j4"))
    await world.dispose()
    world.reboot()

    await world.pump_commands()
    await world.pump_events()

    saga = await world.load_saga("j4")
    assert saga is not None
    assert saga.status is SagaStatus.COMPLETED
    await world.dispose()


@pytest.mark.asyncio
async def test_scheduler_deadline_schedules_retry_without_dispatch(tmp_path: Path) -> None:
    world = SagaSchedulingWorld(tmp_path / "scheduler.db")
    await world.create_schema()

    await world.command_bus.dispatch(StartSchedulerProvisionCommand(scheduler_job_id="j5"))
    world.clock.advance(timedelta(minutes=6))
    assert await world.wiring.timeout_worker.run_once() == 1

    saga = await world.load_saga("j5")
    assert saga is not None
    assert saga.status is SagaStatus.RUNNING
    assert saga.attempt_of(StepName("provision_schedule")) == 1
    assert await world.outbox_command_ids() == [f"{saga.id.value}:provision_schedule:1"]
    assert await world.pending_saga_timeouts() == 1
    await world.dispose()
