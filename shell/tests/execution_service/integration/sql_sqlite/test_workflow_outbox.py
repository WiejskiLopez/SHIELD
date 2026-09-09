"""Outbox e2e: mutacja FSM Workflow przez save() musi zostawić dokładnie 1 wiersz w event_outbox."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from shell.execution_service.domain.execution.aggregates.session_execution.value_objects.project_id_ref import (
    ProjectIdRef,
)
from shell.execution_service.domain.execution.aggregates.session_execution.value_objects.session_id_ref import (
    SessionIdRef,
)
from shell.execution_service.domain.execution.aggregates.workflow.repositories.workflow_repository import (
    WorkflowRepository,
)
from shell.execution_service.domain.execution.aggregates.workflow.value_objects.workflow_id import (
    WorkflowId,
)
from shell.execution_service.domain.execution.aggregates.workflow.workflow import (
    Workflow,
)
from shell.execution_service.infrastructure.execution.persistence.sql.models.base import (
    PERSISTENCE_DELIVERY_MODELS,
    OutboxEventModel,
)
from shell.execution_service.infrastructure.execution.workflow.persistence.sql.unit_of_work import (
    SqlAlchemyWorkflowUnitOfWork,
)
from shell.platform.domain.value_objects.created_at import CreatedAt
from shell.platform.domain.value_objects.occurred_at import OccurredAt

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker

_NOW_DT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_NOW = CreatedAt.from_datetime(_NOW_DT)
_OCCURRED = OccurredAt.from_datetime(_NOW_DT)


def _workflow(wf_id: str) -> Workflow:
    wf = Workflow.create(
        id_=WorkflowId(wf_id),
        now=_NOW,
        session_id=SessionIdRef("session-1"),
        project_id=ProjectIdRef("project-1"),
    )
    wf.pull_events()
    return wf


class TestWorkflowOutbox:
    async def test_finish_writes_one_outbox_row(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyWorkflowUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            wf = _workflow("outbox-wf-finish")
            wf.finish(now=_OCCURRED)
            await uow.save(WorkflowRepository, wf)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("workflow_id") == "outbox-wf-finish"]
        # finish emits 2 events: ChangedEvent + FinishedEvent
        assert len(rows) == 2, f"expected exactly 2 outbox rows for finish, got {len(rows)}"
        event_names = {row.integration_event_name for row in rows}
        assert event_names == {
            "WorkflowChangedIntegrationEvent",
            "WorkflowFinishedIntegrationEvent",
        }

    async def test_fail_writes_one_outbox_row(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyWorkflowUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            wf = _workflow("outbox-wf-fail")
            wf.pull_events()
            wf.fail(now=_OCCURRED)
            await uow.save(WorkflowRepository, wf)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("workflow_id") == "outbox-wf-fail"]
        # fail emits 2 events: ChangedEvent + FailedEvent
        assert len(rows) == 2
        event_names = {row.integration_event_name for row in rows}
        assert event_names == {
            "WorkflowChangedIntegrationEvent",
            "WorkflowFailedIntegrationEvent",
        }

    async def test_abort_writes_one_outbox_row(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyWorkflowUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            wf = _workflow("outbox-wf-abort")
            wf.pull_events()
            wf.abort(now=_OCCURRED)
            await uow.save(WorkflowRepository, wf)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("workflow_id") == "outbox-wf-abort"]
        # abort emits 2 events: ChangedEvent + AbortedEvent
        assert len(rows) == 2
        event_names = {row.integration_event_name for row in rows}
        assert event_names == {
            "WorkflowChangedIntegrationEvent",
            "WorkflowAbortedIntegrationEvent",
        }

    async def test_pause_writes_one_outbox_row(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyWorkflowUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            wf = _workflow("outbox-wf-pause")
            wf.pull_events()
            wf.pause(now=_OCCURRED)
            await uow.save(WorkflowRepository, wf)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("workflow_id") == "outbox-wf-pause"]
        # pause emits 2 events: ChangedEvent + PausedEvent
        assert len(rows) == 2
        event_names = {row.integration_event_name for row in rows}
        assert event_names == {
            "WorkflowChangedIntegrationEvent",
            "WorkflowPausedIntegrationEvent",
        }

    async def test_resume_writes_one_outbox_row(self, session_factory: async_sessionmaker) -> None:
        async with SqlAlchemyWorkflowUnitOfWork(
            session_factory,
            models=PERSISTENCE_DELIVERY_MODELS,
        ) as uow:
            wf = _workflow("outbox-wf-resume")
            wf.pull_events()
            wf.pause(now=_OCCURRED)
            wf.pull_events()
            wf.resume(now=_OCCURRED)
            await uow.save(WorkflowRepository, wf)

        async with session_factory() as session:
            result = await session.execute(select(OutboxEventModel))
            rows = result.scalars().all()

        rows = [row for row in rows if row.payload.get("workflow_id") == "outbox-wf-resume"]
        # resume emits 2 events: ChangedEvent + ResumedEvent
        assert len(rows) == 2
        event_names = {row.integration_event_name for row in rows}
        assert event_names == {
            "WorkflowChangedIntegrationEvent",
            "WorkflowResumedIntegrationEvent",
        }