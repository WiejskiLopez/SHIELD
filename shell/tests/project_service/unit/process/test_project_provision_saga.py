"""Nowy pilot jako test sagi: pełna pętla na prawdziwych klockach serwisu.

Real wiring (install_saga, CommandInboxProcessor, EventInboxProcessor, uczestnicy
na outbox, worker timeoutów) against SQLite. Transport jest symulowany: wiersze
outbox są klonowane do inbox z dedupem jak konsument (odpowiednik relay + broker
+ consumer). Brak brokera w teście. Zastępuje pilotowy test na EventBus.
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
from shell.project_service.application.project.project_provision.command_handlers.provision_workspace_handler import (
    ProvisionWorkspaceHandler,
)
from shell.project_service.application.project.project_provision.command_handlers.release_workspace_handler import (
    ReleaseWorkspaceHandler,
)
from shell.project_service.application.project.project_provision.commands.provision_workspace_command import (
    ProvisionWorkspaceCommand,
)
from shell.project_service.application.project.project_provision.commands.release_workspace_command import (
    ReleaseWorkspaceCommand,
)
from shell.project_service.application.project.project_provision.commands.start_project_provision_command import (
    StartProjectProvisionCommand,
)
from shell.project_service.application.project.project_provision.integration_events.workspace_provision_failed_integration_event import (
    WorkspaceProvisionFailedIntegrationEvent,
)
from shell.project_service.application.project.project_provision.integration_events.workspace_provisioned_integration_event import (
    WorkspaceProvisionedIntegrationEvent,
)
from shell.project_service.application.project.project_provision.integration_events.workspace_released_integration_event import (
    WorkspaceReleasedIntegrationEvent,
)
from shell.project_service.bootstrap.project.command_contracts import (
    PROJECT_COMMAND_CONTRACTS,
    build_project_command_registry,
)
from shell.project_service.bootstrap.project.contract_catalog import (
    PROJECT_CONTRACT_CATALOG,
)
from shell.project_service.bootstrap.project.event_registry import (
    build_project_event_registry,
)
from shell.project_service.infrastructure.project.persistence.sql.models.base import (
    PERSISTENCE_DELIVERY_MODELS,
    SAGA_MODELS,
)
from shell.project_service.infrastructure.project.saga.saga_result_writer import (
    SqlProvisionResultWriter,
)
from shell.project_service.infrastructure.project.saga.saga_wiring import (
    build_project_saga_unit_of_work_factory,
)
from shell.project_service.process.project.project_provision.handlers.provision_result_bridge_handler import (
    ProvisionResultBridgeHandler,
)
from shell.project_service.process.project.project_provision.handlers.release_result_bridge_handler import (
    ReleaseResultBridgeHandler,
)
from shell.project_service.process.project.project_provision.handlers.start_saga_bridge_handler import (
    StartProjectProvisionBridgeHandler,
)
from shell.project_service.process.project.project_provision.saga_definition import (
    PROJECT_PROVISION_STEPS_V2,
    SAGA_TYPE,
)
from shell.project_service.process.project.project_provision.saga_dispatch import (
    ProjectProvisionDispatchResolver,
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


class SagaPilotWorld:
    """Cały serwis w teście: bazy, busy, procesory, wiring install_saga, mosty."""

    def __init__(self, db_path: Path) -> None:
        from shell.project_service.infrastructure.project.persistence.sql.models.base import (
            ProjectSqlAlchemyModelBase,
        )

        self.url = f"sqlite+aiosqlite:///{db_path}"
        self.metadata = ProjectSqlAlchemyModelBase.metadata
        self.session_factory = build_session_factory(self.url)
        self.clock = FakeClock()
        self.ids = FakeIds(prefix="saga")
        self.command_bus = CommandBus()
        self.event_bus = EventBus()
        self.command_registry = build_project_command_registry()
        self.event_registry = build_project_event_registry()
        self.result_writer = SqlProvisionResultWriter(PERSISTENCE_DELIVERY_MODELS.events)
        self.resolver = ProjectProvisionDispatchResolver()
        self.wiring = install_saga(
            uow_factory=build_project_saga_unit_of_work_factory(
                session_factory=lambda: self.session_factory(),
                models=SAGA_MODELS,
                commands_models=PERSISTENCE_DELIVERY_MODELS.commands,
                contracts=PROJECT_COMMAND_CONTRACTS,
                registries={SAGA_TYPE: PROJECT_PROVISION_STEPS_V2},
            ),
            dispatch_resolver=self.resolver,
            clock=self.clock,
            ids=self.ids,
            source_service="project",
            owner="pilot-test-timeout",
        )
        self._wire_buses()
        self._build_processors()

    def _wire_buses(self) -> None:
        self.command_bus.register(
            StartProjectProvisionCommand,
            lambda: StartProjectProvisionBridgeHandler(self.wiring.start_handler),
        )
        self.command_bus.register(
            ProvisionWorkspaceCommand,
            lambda: ProvisionWorkspaceHandler(self.result_writer),
        )
        self.command_bus.register(
            ReleaseWorkspaceCommand,
            lambda: ReleaseWorkspaceHandler(self.result_writer),
        )
        self.event_bus.subscribe(
            WorkspaceProvisionedIntegrationEvent,
            lambda: ProvisionResultBridgeHandler(self.wiring.advance_handler),
        )
        self.event_bus.subscribe(
            WorkspaceProvisionFailedIntegrationEvent,
            lambda: ProvisionResultBridgeHandler(self.wiring.advance_handler),
        )
        self.event_bus.subscribe(
            WorkspaceReleasedIntegrationEvent,
            lambda: ReleaseResultBridgeHandler(self.wiring.advance_handler),
        )

    def _build_processors(self) -> None:
        self.command_processor = CommandInboxProcessor(
            session_factory=self.session_factory,
            dispatcher=CommandBusPublisher(self.command_bus),
            models=PERSISTENCE_DELIVERY_MODELS.commands,
            registry=self.command_registry,
            worker_id="pilot-command-processor",
            upcaster=PayloadUpcaster(),
        )
        self.event_processor = EventInboxProcessor(
            session_factory=self.session_factory,
            event_bus=self.event_bus,
            models=PERSISTENCE_DELIVERY_MODELS.events,
            registry=self.event_registry,
            worker_id="pilot-event-processor",
            envelope_policy=envelope_policy_from_catalog(PROJECT_CONTRACT_CATALOG),
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

    async def load_saga(self, project_id: str) -> Saga | None:
        uow = self.wiring.uow_factory()
        try:
            async with uow:
                return await uow.sagas.get_by_key(
                    SagaKey(saga_type=SAGA_TYPE, business_key=project_id)
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
async def test_pilot_happy_path(tmp_path: Path) -> None:
    world = SagaPilotWorld(tmp_path / "pilot.db")
    await world.create_schema()

    await world.command_bus.dispatch(StartProjectProvisionCommand(project_id="p1"))
    await world.pump_commands()
    await world.pump_events()

    saga = await world.load_saga("p1")
    assert saga is not None
    assert saga.status is SagaStatus.COMPLETED
    assert await world.outbox_command_ids() == [f"{saga.id.value}:provision_workspace:1"]
    await world.dispose()


@pytest.mark.asyncio
async def test_pilot_failure_compensates_with_worker_retry(tmp_path: Path) -> None:
    world = SagaPilotWorld(tmp_path / "pilot.db")
    await world.create_schema()

    await world.command_bus.dispatch(StartProjectProvisionCommand(project_id="p2", fail=True))
    await world.pump_commands()
    await world.pump_events()

    world.clock.advance(timedelta(seconds=31))
    assert await world.wiring.timeout_worker.run_once() == 1
    assert await world.inbox_command_attempts("project.project_provision.provision_workspace") == [
        1
    ]
    await world.pump_commands()
    assert await world.inbox_command_attempts("project.project_provision.provision_workspace") == [
        1,
        2,
    ]
    await world.pump_events()

    saga = await world.load_saga("p2")
    assert saga is not None
    assert saga.status is SagaStatus.COMPENSATING
    await world.pump_commands()
    await world.pump_events()

    saga = await world.load_saga("p2")
    assert saga is not None
    assert saga.status is SagaStatus.COMPENSATED
    assert await world.outbox_command_ids() == [
        f"{saga.id.value}:provision_workspace:1",
        f"{saga.id.value}:provision_workspace:2",
        f"{saga.id.value}:release_workspace:1",
    ]
    await world.dispose()


@pytest.mark.asyncio
async def test_pilot_duplicate_result_is_noop(tmp_path: Path) -> None:
    world = SagaPilotWorld(tmp_path / "pilot.db")
    await world.create_schema()

    await world.command_bus.dispatch(StartProjectProvisionCommand(project_id="p3"))
    await world.pump_commands()
    await world.pump_events()

    duplicate = WorkspaceProvisionedIntegrationEvent(
        event_id="dup-1",
        correlation_id="corr-dup",
        causation_id="cause-dup",
        occurred_at=_now(),
        aggregate_id="p3",
        schema_version=1,
        project_id="p3",
        attempt=1,
    )
    bridge = ProvisionResultBridgeHandler(world.wiring.advance_handler)
    await bridge.handle(duplicate)
    await bridge.handle(duplicate)

    saga = await world.load_saga("p3")
    assert saga is not None
    assert saga.status is SagaStatus.COMPLETED
    assert len(await world.outbox_command_ids()) == 1
    await world.dispose()


@pytest.mark.asyncio
async def test_pilot_restart_resumes_midflight(tmp_path: Path) -> None:
    world = SagaPilotWorld(tmp_path / "pilot.db")
    await world.create_schema()

    await world.command_bus.dispatch(StartProjectProvisionCommand(project_id="p4"))
    await world.dispose()
    world.reboot()

    await world.pump_commands()
    await world.pump_events()

    saga = await world.load_saga("p4")
    assert saga is not None
    assert saga.status is SagaStatus.COMPLETED
    await world.dispose()


@pytest.mark.asyncio
async def test_pilot_deadline_schedules_retry_without_dispatch(tmp_path: Path) -> None:
    world = SagaPilotWorld(tmp_path / "pilot.db")
    await world.create_schema()

    await world.command_bus.dispatch(StartProjectProvisionCommand(project_id="p5"))
    world.clock.advance(timedelta(minutes=6))
    assert await world.wiring.timeout_worker.run_once() == 1

    saga = await world.load_saga("p5")
    assert saga is not None
    assert saga.status is SagaStatus.RUNNING
    assert saga.attempt_of(StepName("provision_workspace")) == 1
    assert await world.outbox_command_ids() == [f"{saga.id.value}:provision_workspace:1"]
    assert await world.pending_saga_timeouts() == 1
    await world.dispose()
