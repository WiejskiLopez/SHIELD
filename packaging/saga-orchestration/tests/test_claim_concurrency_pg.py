from __future__ import annotations

import asyncio
import os
from datetime import timedelta

import pytest
from saga_orchestration.application.start_saga_handler import (
    StartSagaCommand,
    StartSagaHandler,
)
from saga_orchestration.domain.ports.outbox_writer import (
    CommandOutboxWriter,
    OutboxCommandRow,
)
from saga_orchestration.domain.saga_key import SagaKey
from saga_orchestration.domain.saga_payload import SagaPayload
from saga_orchestration.domain.saga_status import SagaStatus
from saga_orchestration.domain.step import StepDefinition, StepRegistry
from saga_orchestration.domain.step_name import StepName
from saga_orchestration.infrastructure.in_memory.fake_clock import FakeClock, FakeIds
from saga_orchestration.infrastructure.saga_timeout_worker import SagaTimeoutWorker
from saga_orchestration.infrastructure.sqlalchemy.saga_models import build_saga_models
from saga_orchestration.infrastructure.sqlalchemy.sql_saga_uow import SqlSagaUnitOfWork
from saga_test_kit import default_resolver
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

SAGA_TYPE = "pg_claim_case"


def single_step_registry() -> StepRegistry:
    """Jeden krok BEZ kompensaty: deadline prowadzi do FAILED (ścieżka terminalna)."""
    return StepRegistry(
        steps=(
            StepDefinition(
                name=StepName("provision_workspace"),
                target_service="project",
                timeout=timedelta(minutes=5),
                max_attempts=1,
            ),
        )
    )


REQUIRES_PG = os.environ.get("POSTGRES_TEST_URL") is None
SKIP_REASON = "POSTGRES_TEST_URL nie ustawione — test współbieżności claimu wymaga PG"

pytestmark = pytest.mark.skipif(REQUIRES_PG, reason=SKIP_REASON)


class Base(DeclarativeBase):
    pass


class CollectingWriter(CommandOutboxWriter):
    def __init__(self, rows: list[OutboxCommandRow]) -> None:
        self._rows = rows

    def append(self, row: OutboxCommandRow) -> None:
        self._rows.append(row)


@pytest.mark.asyncio
async def test_parallel_claim_processes_each_timeout_once() -> None:
    url = os.environ["POSTGRES_TEST_URL"]
    engine = create_async_engine(url, pool_size=10)
    models = build_saga_models(Base)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        await session.execute(delete(models.delivery))
        await session.execute(delete(models.timeout))
        await session.execute(delete(models.instance))
        await session.commit()

    clock = FakeClock()
    registries = {SAGA_TYPE: single_step_registry()}
    rows: list[OutboxCommandRow] = []
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    def factory() -> SqlSagaUnitOfWork:
        return SqlSagaUnitOfWork(
            sessions(), models, CollectingWriter(rows), registries, owns_session=True
        )

    ids = FakeIds()
    resolver = default_resolver()
    start = StartSagaHandler(factory, clock, ids, resolver, "test")

    saga_count = 8
    keys = [SagaKey(saga_type=SAGA_TYPE, business_key=f"pg-{index}") for index in range(saga_count)]
    for key in keys:
        await start.handle(
            StartSagaCommand(
                key=key,
                payload=SagaPayload({"business_key": key.business_key}),
                steps=single_step_registry(),
                correlation_id="corr-pg",
                causation_id=None,
            )
        )
    clock.advance(timedelta(minutes=6))

    async def run_worker(number: int) -> int:
        worker = SagaTimeoutWorker(
            factory,
            clock,
            resolver,
            ids,
            "test",
            f"pg-worker-{number}",
            timedelta(minutes=1),
            100,
        )
        return await worker.run_once()

    processed = await asyncio.gather(*(run_worker(number) for number in range(4)))

    assert sum(processed) == saga_count
    async with factory() as uow:
        for key in keys:
            saga = await uow.sagas.get_by_key(key)
            assert saga is not None
            assert saga.status is SagaStatus.FAILED
            assert saga.version.value == 3
    async with sessions() as session:
        delivery_total = await session.execute(select(func.count()).select_from(models.delivery))
        assert int(delivery_total.scalar_one()) == saga_count
    assert len(rows) == saga_count
    await engine.dispose()
