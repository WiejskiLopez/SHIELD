"""Outbox e2e: mutacja FSM TaskExecution przez save() emituje dwa rekordy."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from shell.execution_service.domain.execution.aggregates.task_execution.repositories.task_execution_repository import (
    TaskExecutionRepository,
)
from shell.execution_service.domain.execution.aggregates.task_execution.task_execution import (
    TaskExecution,
)
from shell.execution_service.domain.execution.aggregates.task_execution.value_objects.task_execution_id import (
    TaskExecutionId,
)
from shell.execution_service.domain.execution.aggregates.task_execution.value_objects.task_name import (
    TaskName,
)
from shell.execution_service.domain.execution.aggregates.task_execution.value_objects.work_dir import (
    WorkDir,
)
from shell.execution_service.domain.execution.aggregates.workflow.value_objects.workflow_id import (
    WorkflowId,
)
from shell.execution_service.infrastructure.execution.persistence.sql.models.base import (
    PERSISTENCE_DELIVERY_MODELS,
    OutboxEventModel,
)
from shell.execution_service.infrastructure.execution.task_execution.persistence.sql.unit_of_work import (
    SqlAlchemyTaskExecutionUnitOfWork,
)
from shell.platform.domain.value_objects.created_at import CreatedAt
from shell.platform.domain.value_objects.occurred_at import OccurredAt

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker

_NOW_DT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_NOW = CreatedAt.from_datetime(_NOW_DT)
_OCCURRED = OccurredAt.from_datetime(_NOW_DT)


def _task(task_id: str) -> TaskExecution:
    task = TaskExecution.create(
        id_=TaskExecutionId(task_id),
        name=TaskName("test-task"),
        now=_NOW,
        workflow_id=WorkflowId("workflow-1"),
        work_dir=WorkDir("workdir/sample"),
    )
    task.pull_events()
    return task


class TestTaskExecutionOutbox:
    async def test_start_writes_two_outbox_rows(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyTaskExecutionUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            task = _task("outbox-task-start")
            task.start(now=_OCCURRED)
            await uow.save(TaskExecutionRepository, task)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("task_execution_id") == "outbox-task-start"]
        assert len(rows) == 2, f"expected exactly 2 outbox rows, got {len(rows)}"
        assert rows[0].payload.get("task_execution_id") == "outbox-task-start"
        assert rows[0].integration_event_name == "TaskExecutionChangedIntegrationEvent"

    async def test_complete_writes_two_outbox_rows(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyTaskExecutionUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            task = _task("outbox-task-complete")
            task.start(now=_OCCURRED)
            task.pull_events()
            task.complete(now=_OCCURRED)
            await uow.save(TaskExecutionRepository, task)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("task_execution_id") == "outbox-task-complete"]
        assert len(rows) == 2
        assert rows[0].payload.get("task_execution_id") == "outbox-task-complete"
        assert rows[0].integration_event_name == "TaskExecutionChangedIntegrationEvent"

    async def test_fail_writes_two_outbox_rows(self, session_factory: async_sessionmaker) -> None:
        from shell.platform.domain.value_objects.reason import Reason

        async with SqlAlchemyTaskExecutionUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            task = _task("outbox-task-fail")
            task.start(now=_OCCURRED)
            task.pull_events()
            task.fail(reason=Reason("test failure"), now=_OCCURRED)
            await uow.save(TaskExecutionRepository, task)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("task_execution_id") == "outbox-task-fail"]
        assert len(rows) == 2
        assert rows[0].payload.get("task_execution_id") == "outbox-task-fail"
        assert rows[0].integration_event_name == "TaskExecutionChangedIntegrationEvent"

    async def test_timeout_writes_two_outbox_rows(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyTaskExecutionUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            task = _task("outbox-task-timeout")
            task.start(now=_OCCURRED)
            task.pull_events()
            task.timeout(now=_OCCURRED)
            await uow.save(TaskExecutionRepository, task)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("task_execution_id") == "outbox-task-timeout"]
        assert len(rows) == 2
        assert rows[0].payload.get("task_execution_id") == "outbox-task-timeout"
        assert rows[0].integration_event_name == "TaskExecutionChangedIntegrationEvent"

    async def test_exhaust_writes_two_outbox_rows(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyTaskExecutionUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            task = _task("outbox-task-exhaust")
            task.start(now=_OCCURRED)
            task.pull_events()
            task.exhaust(now=_OCCURRED)
            await uow.save(TaskExecutionRepository, task)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("task_execution_id") == "outbox-task-exhaust"]
        assert len(rows) == 2
        assert rows[0].payload.get("task_execution_id") == "outbox-task-exhaust"
        assert rows[0].integration_event_name == "TaskExecutionChangedIntegrationEvent"

    async def test_rename_writes_two_outbox_rows(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyTaskExecutionUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            task = _task("outbox-task-rename")
            task.pull_events()
            task.rename(new_name=TaskName("renamed"), now=_OCCURRED)
            await uow.save(TaskExecutionRepository, task)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("task_execution_id") == "outbox-task-rename"]
        # rename emits 2 events: ChangedEvent + RenamedEvent
        assert len(rows) == 2, f"expected exactly 2 outbox rows for rename, got {len(rows)}"
        event_names = {row.integration_event_name for row in rows}
        assert event_names == {
            "TaskExecutionChangedIntegrationEvent",
            "TaskExecutionRenamedIntegrationEvent",
        }