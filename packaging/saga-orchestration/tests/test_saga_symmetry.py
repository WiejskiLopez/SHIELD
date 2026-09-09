from __future__ import annotations

import pytest
from saga_orchestration.application.advance_saga_handler import AdvanceSagaCommand
from saga_orchestration.application.start_saga_handler import StartSagaCommand
from saga_orchestration.domain.processed_delivery import DeliveryId
from saga_orchestration.domain.saga_key import SagaKey
from saga_orchestration.domain.saga_payload import SagaPayload
from saga_orchestration.domain.saga_status import SagaStatus
from saga_orchestration.infrastructure.sqlalchemy.saga_models import build_saga_models
from saga_test_kit import (
    NOTIFY,
    PROVISION,
    DictResolver,
    InMemoryHarness,
    SqlHarness,
    two_step_registry,
)
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

SAGA_TYPE = "symmetry_case"


class Base(DeclarativeBase):
    pass


class Base2(DeclarativeBase):
    pass


Harness = InMemoryHarness | SqlHarness


def make_key() -> SagaKey:
    return SagaKey(saga_type=SAGA_TYPE, business_key="sym-1")


def outbox_ids(harness: Harness) -> list[str]:
    if isinstance(harness, InMemoryHarness):
        return [row.command_id for row in harness.store.outbox]
    return [row.command_id for row in harness.rows]


async def journal_count(harness: Harness, saga_id_value: str) -> int:
    from saga_orchestration.domain.saga_id import SagaId

    count = 0
    async with harness.factory() as uow:
        for delivery in ("evt-1", "evt-stale", "fail-1"):
            if await uow.sagas.is_delivery_processed(SagaId(saga_id_value), DeliveryId(delivery)):
                count += 1
    return count


async def run_happy_path(harness: Harness) -> dict[str, object]:
    start, advance, _ = harness.handlers()
    key = make_key()

    def start_cmd() -> StartSagaCommand:
        return StartSagaCommand(
            key=key,
            payload=SagaPayload({"business_key": key.business_key}),
            steps=two_step_registry(),
            correlation_id="corr-1",
            causation_id=None,
        )

    await start.handle(start_cmd())
    await start.handle(start_cmd())

    async def advance_once(delivery: str) -> None:
        await advance.handle(
            AdvanceSagaCommand(
                key=key,
                delivery_id=DeliveryId(delivery),
                step=PROVISION,
                attempt=1,
                succeeded=True,
                is_compensation=False,
                correlation_id="corr-1",
                causation_id=None,
            )
        )

    await advance_once("evt-1")
    await advance_once("evt-1")
    await advance_once("evt-stale")

    async with harness.factory() as uow:
        saga = await uow.sagas.get_by_key(key)
    assert saga is not None
    return {
        "status": saga.status,
        "current": saga.current_step,
        "completed": saga.completed_steps,
        "version": saga.version.value,
        "outbox": outbox_ids(harness),
        "journal": await journal_count(harness, saga.id.value),
    }


async def run_failure_path(harness: Harness) -> dict[str, object]:
    start, advance, _ = harness.handlers()
    key = make_key()
    await start.handle(
        StartSagaCommand(
            key=key,
            payload=SagaPayload({"business_key": key.business_key}),
            steps=two_step_registry(max_attempts_provision=1),
            correlation_id="corr-1",
            causation_id=None,
        )
    )
    await advance.handle(
        AdvanceSagaCommand(
            key=key,
            delivery_id=DeliveryId("prov-ok"),
            step=PROVISION,
            attempt=1,
            succeeded=True,
            is_compensation=False,
            correlation_id="corr-1",
            causation_id=None,
        )
    )
    await advance.handle(
        AdvanceSagaCommand(
            key=key,
            delivery_id=DeliveryId("fail-1"),
            step=NOTIFY,
            attempt=1,
            succeeded=False,
            is_compensation=False,
            correlation_id="corr-1",
            causation_id=None,
        )
    )
    async with harness.factory() as uow:
        saga = await uow.sagas.get_by_key(key)
    assert saga is not None
    return {
        "status": saga.status,
        "current": saga.current_step,
        "version": saga.version.value,
        "failed": saga.failed_steps,
        "outbox": outbox_ids(harness),
    }


@pytest.mark.asyncio
async def test_symmetry_happy_path() -> None:
    memory = InMemoryHarness({SAGA_TYPE: two_step_registry()})
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    models = build_saga_models(Base)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sql = SqlHarness(engine, models, {SAGA_TYPE: two_step_registry()})

    expected = await run_happy_path(memory)
    actual = await run_happy_path(sql)

    assert actual["status"] is SagaStatus.RUNNING
    assert actual == expected
    await engine.dispose()


@pytest.mark.asyncio
async def test_symmetry_failure_path() -> None:
    memory = InMemoryHarness({SAGA_TYPE: two_step_registry(max_attempts_provision=1)})
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    models = build_saga_models(Base2)
    async with engine.begin() as connection:
        await connection.run_sync(Base2.metadata.create_all)
    sql = SqlHarness(engine, models, {SAGA_TYPE: two_step_registry(max_attempts_provision=1)})

    assert await run_failure_path(sql) == await run_failure_path(memory)
    assert (await run_failure_path(memory))["status"] is SagaStatus.COMPENSATING
    await engine.dispose()


def test_resolver_contract_types_cover_registry() -> None:
    from saga_orchestration.domain.saga_payload import SagaPayload

    resolver = DictResolver({})
    key = make_key()
    empty = SagaPayload.empty()
    assert resolver.for_step(key, empty, PROVISION, 1).contract_type == "provision_workspace.do"
    assert resolver.for_step(key, empty, NOTIFY, 1).destination_service == "project"
