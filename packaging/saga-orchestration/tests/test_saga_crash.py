from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from saga_orchestration.application.advance_saga_handler import (
    AdvanceSagaCommand,
    AdvanceSagaHandler,
)
from saga_orchestration.application.start_saga_handler import (
    StartSagaCommand,
    StartSagaHandler,
)
from saga_orchestration.application.timeout_saga_handler import TimeoutSagaHandler
from saga_orchestration.domain.ports.outbox_writer import (
    CommandOutboxWriter,
    OutboxCommandRow,
)
from saga_orchestration.domain.processed_delivery import DeliveryId
from saga_orchestration.domain.saga_key import SagaKey
from saga_orchestration.domain.saga_payload import SagaPayload
from saga_orchestration.domain.saga_status import SagaStatus
from saga_orchestration.infrastructure.in_memory.fake_clock import FakeClock, FakeIds
from saga_orchestration.infrastructure.sqlalchemy.saga_models import SagaModels, build_saga_models
from saga_orchestration.infrastructure.sqlalchemy.sql_saga_uow import SqlSagaUnitOfWork
from saga_test_kit import NOTIFY, PROVISION, default_resolver, two_step_registry
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

if TYPE_CHECKING:
    from pathlib import Path

    from saga_orchestration.domain.step_name import StepName

SAGA_TYPE = "crash_case"


class Base(DeclarativeBase):
    pass


class BaseAtomic(DeclarativeBase):
    pass


def make_key() -> SagaKey:
    return SagaKey(saga_type=SAGA_TYPE, business_key="crash-1")


class CollectingWriter(CommandOutboxWriter):
    def __init__(self, rows: list[OutboxCommandRow]) -> None:
        self._rows = rows

    def append(self, row: OutboxCommandRow) -> None:
        self._rows.append(row)


class ExplodingWriter(CommandOutboxWriter):
    def append(self, row: OutboxCommandRow) -> None:
        raise RuntimeError("outbox down")


class FileHarness:
    """Proces na plikowej bazie: kill = dispose silnika, reboot = nowy silnik."""

    def __init__(
        self,
        db_path: Path,
        base: type[DeclarativeBase],
        writer: CommandOutboxWriter | None = None,
    ) -> None:
        self.engine: AsyncEngine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        self.models: SagaModels = build_saga_models(base)
        self._base = base
        self.registries = {SAGA_TYPE: two_step_registry()}
        self.clock = FakeClock()
        self.ids = FakeIds()
        self.resolver = default_resolver()
        self.rows: list[OutboxCommandRow] = []
        self.writer: CommandOutboxWriter = (
            writer if writer is not None else CollectingWriter(self.rows)
        )
        self._sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def create_schema(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(self._base.metadata.create_all)

    def factory(self) -> SqlSagaUnitOfWork:
        return SqlSagaUnitOfWork(
            self._sessions(),
            self.models,
            self.writer,
            self.registries,
            owns_session=True,
        )

    def handlers(self) -> tuple[StartSagaHandler, AdvanceSagaHandler, TimeoutSagaHandler]:
        def factory() -> SqlSagaUnitOfWork:
            return self.factory()

        return (
            StartSagaHandler(factory, self.clock, self.ids, self.resolver, "test"),
            AdvanceSagaHandler(factory, self.clock, self.resolver, self.ids, "test"),
            TimeoutSagaHandler(factory, self.clock, self.resolver, self.ids, "test"),
        )

    async def kill(self) -> None:
        await self.engine.dispose()

    async def reboot(self, db_path: Path) -> None:
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        self._sessions = async_sessionmaker(self.engine, expire_on_commit=False)


async def deliver(
    advance: AdvanceSagaHandler, key: SagaKey, delivery: str, step: StepName, ok: bool
) -> None:
    await advance.handle(
        AdvanceSagaCommand(
            key=key,
            delivery_id=DeliveryId(delivery),
            step=step,
            attempt=1,
            succeeded=ok,
            is_compensation=False,
            correlation_id="corr-1",
            causation_id=None,
        )
    )


@pytest.mark.asyncio
async def test_crash_between_commits_resumes_to_completed(tmp_path: Path) -> None:
    db_path = tmp_path / "saga.db"
    harness = FileHarness(db_path, Base)
    await harness.create_schema()
    start, advance, _ = harness.handlers()
    key = make_key()

    await start.handle(
        StartSagaCommand(
            key=key,
            payload=SagaPayload({"business_key": key.business_key}),
            steps=two_step_registry(),
            correlation_id="corr-1",
            causation_id=None,
        )
    )
    await harness.kill()
    await harness.reboot(db_path)

    await deliver(advance, key, "evt-1", PROVISION, True)
    await harness.kill()
    await harness.reboot(db_path)

    await deliver(advance, key, "evt-1", PROVISION, True)
    await deliver(advance, key, "evt-2", NOTIFY, True)

    async with harness.factory() as uow:
        saga = await uow.sagas.get_by_key(key)
    assert saga is not None
    assert saga.status is SagaStatus.COMPLETED
    assert saga.completed_steps == (PROVISION, NOTIFY)
    assert [row.command_id for row in harness.rows] == [
        f"{saga.id.value}:provision_workspace:1",
        f"{saga.id.value}:notify_owner:1",
    ]
    await harness.kill()


@pytest.mark.asyncio
async def test_atomic_start_on_sql_leaves_no_orphans(tmp_path: Path) -> None:
    db_path = tmp_path / "atomic.db"
    harness = FileHarness(db_path, BaseAtomic, writer=ExplodingWriter())
    await harness.create_schema()
    start, _, _ = harness.handlers()
    key = make_key()

    with pytest.raises(RuntimeError, match="outbox down"):
        await start.handle(
            StartSagaCommand(
                key=key,
                payload=SagaPayload({"business_key": key.business_key}),
                steps=two_step_registry(),
                correlation_id="corr-1",
                causation_id=None,
            )
        )

    async with harness.factory() as uow:
        assert await uow.sagas.get_by_key(key) is None
    await harness.kill()
