from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from saga_orchestration.application.advance_saga_handler import AdvanceSagaHandler
from saga_orchestration.application.start_saga_handler import StartSagaHandler
from saga_orchestration.application.step_dispatch import StepDispatch, StepDispatchResolver
from saga_orchestration.application.timeout_saga_handler import TimeoutSagaHandler
from saga_orchestration.domain.ports.outbox_writer import (
    CommandOutboxWriter,
    OutboxCommandRow,
)
from saga_orchestration.domain.step import StepDefinition, StepRegistry
from saga_orchestration.domain.step_name import StepName
from saga_orchestration.infrastructure.in_memory.fake_clock import FakeClock, FakeIds
from saga_orchestration.infrastructure.in_memory.in_memory_saga_uow import (
    InMemorySagaUnitOfWork,
)
from saga_orchestration.infrastructure.in_memory.in_memory_store import SagaMemoryStore
from saga_orchestration.infrastructure.saga_timeout_worker import SagaTimeoutWorker
from saga_orchestration.infrastructure.sqlalchemy.sql_saga_uow import SqlSagaUnitOfWork
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

if TYPE_CHECKING:
    from collections.abc import Mapping

    from saga_orchestration.domain.json_value import JsonValue
    from saga_orchestration.domain.saga_key import SagaKey
    from saga_orchestration.domain.saga_payload import SagaPayload
    from saga_orchestration.domain.saga_timeout import ClaimedTimeout
    from saga_orchestration.infrastructure.sqlalchemy.saga_models import SagaModels

PROVISION = StepName("provision_workspace")
RELEASE = StepName("release_workspace")
NOTIFY = StepName("notify_owner")
STEP_A = StepName("step_a")
STEP_B = StepName("step_b")
STEP_C = StepName("step_c")
UNDO_A = StepName("undo_a")
UNDO_B = StepName("undo_b")


def two_step_registry(max_attempts_provision: int = 2) -> StepRegistry:
    return StepRegistry(
        steps=(
            StepDefinition(
                name=PROVISION,
                target_service="project",
                compensation_step=RELEASE,
                timeout=timedelta(minutes=5),
                max_attempts=max_attempts_provision,
                backoff=timedelta(seconds=30),
            ),
            StepDefinition(
                name=NOTIFY,
                target_service="notify",
                timeout=timedelta(minutes=5),
            ),
        )
    )


def three_step_registry(max_attempts_b: int = 1) -> StepRegistry:
    return StepRegistry(
        steps=(
            StepDefinition(name=STEP_A, target_service="svc", compensation_step=UNDO_A),
            StepDefinition(
                name=STEP_B,
                target_service="svc",
                compensation_step=UNDO_B,
                max_attempts=max_attempts_b,
            ),
            StepDefinition(name=STEP_C, target_service="svc"),
        )
    )


class DictResolver(StepDispatchResolver):
    """Statyczny resolver testowy: krok -> kontrakt. Payload z klucza biznesowego."""

    def __init__(self, service_by_step: Mapping[str, str]) -> None:
        self._service_by_step = dict(service_by_step)

    def for_step(
        self, key: SagaKey, payload: SagaPayload, step: StepName, attempt: int
    ) -> StepDispatch:
        _ = attempt
        data: dict[str, JsonValue] = {"business_key": key.business_key}
        marker = payload.data.get("marker")
        if isinstance(marker, str) and marker:
            data["marker"] = marker
        return StepDispatch(
            contract_type=f"{step.value}.do",
            destination_service=self._service_by_step.get(step.value, "project"),
            payload=data,
            aggregate_id=key.business_key,
        )


def default_resolver() -> DictResolver:
    return DictResolver(
        {
            PROVISION.value: "project",
            RELEASE.value: "project",
            NOTIFY.value: "notify",
            STEP_A.value: "svc",
            STEP_B.value: "svc",
            STEP_C.value: "svc",
            UNDO_A.value: "svc",
            UNDO_B.value: "svc",
        }
    )


class InMemoryHarness:
    def __init__(self, registries: Mapping[str, StepRegistry], source: str = "test") -> None:
        self.store = SagaMemoryStore()
        self.clock = FakeClock()
        self.ids = FakeIds()
        self.resolver = default_resolver()
        self.registries = dict(registries)
        self.source = source

    def factory(self) -> InMemorySagaUnitOfWork:
        return InMemorySagaUnitOfWork(self.store, self.registries)

    def handlers(self) -> tuple[StartSagaHandler, AdvanceSagaHandler, TimeoutSagaHandler]:
        def factory() -> InMemorySagaUnitOfWork:
            return self.factory()

        start = StartSagaHandler(factory, self.clock, self.ids, self.resolver, self.source)
        advance = AdvanceSagaHandler(factory, self.clock, self.resolver, self.ids, self.source)
        timeout = TimeoutSagaHandler(factory, self.clock, self.resolver, self.ids, self.source)
        return start, advance, timeout

    def worker(self, owner: str = "test-worker") -> SagaTimeoutWorker:
        def factory() -> InMemorySagaUnitOfWork:
            return self.factory()

        return SagaTimeoutWorker(
            factory,
            self.clock,
            self.resolver,
            self.ids,
            self.source,
            owner,
            timedelta(minutes=1),
            100,
        )


async def claim_due_rows(
    harness: InMemoryHarness | SqlHarness, owner: str = "test-owner", limit: int = 100
) -> list[ClaimedTimeout]:
    """Claim wszystkiego dojrzałego (osobna transakcja, jak worker)."""
    uow = harness.factory()
    try:
        async with uow:
            rows = await uow.timeouts.claim_due(
                owner=owner,
                now=harness.clock.now(),
                lease_until=harness.clock.now() + timedelta(minutes=1),
                limit=limit,
            )
    finally:
        await uow.close()
    return list(rows)


class CollectingWriter(CommandOutboxWriter):
    """Writer testowy: zbiera wiersze na listę (sesja SQL flushuje je z transakcją)."""

    def __init__(self, rows: list[OutboxCommandRow]) -> None:
        self._rows = rows

    def append(self, row: OutboxCommandRow) -> None:
        self._rows.append(row)


class SqlHarness:
    """Backend SQL na współdzielonym silniku. Sesja per UoW (owns_session=True)."""

    def __init__(
        self,
        engine: AsyncEngine,
        models: SagaModels,
        registries: Mapping[str, StepRegistry],
        source: str = "test",
    ) -> None:
        self._sessions = async_sessionmaker(engine, expire_on_commit=False)
        self._models = models
        self._registries = dict(registries)
        self.clock = FakeClock()
        self.ids = FakeIds()
        self.resolver = default_resolver()
        self.source = source
        self.rows: list[OutboxCommandRow] = []

    def factory(self) -> SqlSagaUnitOfWork:
        return SqlSagaUnitOfWork(
            self._sessions(),
            self._models,
            CollectingWriter(self.rows),
            self._registries,
            owns_session=True,
        )

    def handlers(self) -> tuple[StartSagaHandler, AdvanceSagaHandler, TimeoutSagaHandler]:
        def factory() -> SqlSagaUnitOfWork:
            return self.factory()

        start = StartSagaHandler(factory, self.clock, self.ids, self.resolver, self.source)
        advance = AdvanceSagaHandler(factory, self.clock, self.resolver, self.ids, self.source)
        timeout = TimeoutSagaHandler(factory, self.clock, self.resolver, self.ids, self.source)
        return start, advance, timeout
