"""Workflow — agregat workflow (FSM).

Agregat reprezentujący workflow jako maszynę stanów finite-state machine (FSM) z przejściami:
ACTIVE -> COMPLETED | FAILED | ABORTED | PAUSED. Przechowuje stan workflow oraz odniesienia
do session_id i project_id. Każde przejście stanu inicjuje zdarzenie domenowe, które warstwa
aplikacji pobiera po udanej transakcji przez ``pull_events`` do wydawcy / outbox.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from shell.execution_service.domain.execution.aggregates.workflow.events.workflow_aborted_event import (
    WorkflowAbortedEvent,
)
from shell.execution_service.domain.execution.aggregates.workflow.events.workflow_changed_event import (
    WorkflowChangedEvent,
)
from shell.execution_service.domain.execution.aggregates.workflow.events.workflow_created_event import (
    WorkflowCreatedEvent,
)
from shell.execution_service.domain.execution.aggregates.workflow.events.workflow_deleted_event import (
    WorkflowDeletedEvent,
)
from shell.execution_service.domain.execution.aggregates.workflow.events.workflow_failed_event import (
    WorkflowFailedEvent,
)
from shell.execution_service.domain.execution.aggregates.workflow.events.workflow_finished_event import (
    WorkflowFinishedEvent,
)
from shell.execution_service.domain.execution.aggregates.workflow.events.workflow_paused_event import (
    WorkflowPausedEvent,
)
from shell.execution_service.domain.execution.aggregates.workflow.events.workflow_resumed_event import (
    WorkflowResumedEvent,
)
from shell.execution_service.domain.execution.aggregates.workflow.value_objects.workflow_id import (
    WorkflowId,
)
from shell.execution_service.domain.execution.aggregates.workflow.value_objects.workflow_status import (
    WorkflowStatus,
)
from shell.platform.domain.base import AggregateRoot
from shell.platform.domain.exceptions.domain_error import DomainError
from shell.platform.domain.value_objects.changed_at import NONE_CHANGED_AT, ChangedAt
from shell.platform.domain.value_objects.created_at import CreatedAt
from shell.platform.domain.value_objects.deleted_at import NONE_DELETED_AT, DeletedAt
from shell.platform.domain.value_objects.occurred_at import OccurredAt

if TYPE_CHECKING:
    from shell.execution_service.domain.execution.aggregates.session_execution.value_objects.project_id_ref import (
        ProjectIdRef,
    )
    from shell.execution_service.domain.execution.aggregates.session_execution.value_objects.session_id_ref import (
        SessionIdRef,
    )


class Workflow(AggregateRoot[WorkflowId]):
    __slots__ = (
        "_created_at",
        "_changed_at",
        "_deleted_at",
        "_session_id",
        "_project_id",
        "_status",
    )

    _session_id: SessionIdRef
    _project_id: ProjectIdRef
    _status: WorkflowStatus
    _created_at: CreatedAt
    _changed_at: ChangedAt

    def __init__(
        self,
        *,
        id: WorkflowId,
        created_at: CreatedAt,
        changed_at: ChangedAt = NONE_CHANGED_AT,
        deleted_at: DeletedAt = NONE_DELETED_AT,
        session_id: SessionIdRef,
        project_id: ProjectIdRef,
        status: WorkflowStatus,
    ) -> None:
        super().__init__(id)
        self._session_id = session_id
        self._project_id = project_id
        self._status = status
        self._created_at = created_at
        self._changed_at = changed_at
        self._deleted_at = deleted_at

    @classmethod
    def create(
        cls,
        *,
        id_: WorkflowId,
        now: CreatedAt,
        session_id: SessionIdRef,
        project_id: ProjectIdRef,
    ) -> Workflow:
        return cls._new(
            id_=id_,
            now=OccurredAt.from_datetime(now.value),
            session_id=session_id,
            project_id=project_id,
        )

    @classmethod
    def _new(
        cls,
        *,
        id_: WorkflowId,
        now: OccurredAt,
        session_id: SessionIdRef,
        project_id: ProjectIdRef,
    ) -> Workflow:
        workflow = cls(
            id=id_,
            session_id=session_id,
            project_id=project_id,
            status=WorkflowStatus.ACTIVE,
            created_at=CreatedAt.from_datetime(now.value),
        )
        workflow.append_event(
            WorkflowCreatedEvent.now(workflow_id=id_, now=OccurredAt.from_datetime(now.value))
        )
        return workflow

    # --- Methods ---

    def finish(self, now: OccurredAt) -> None:
        if self._deleted_at.value is not None:
            raise DomainError("Workflow already deleted")
        if self._status != WorkflowStatus.ACTIVE:
            raise DomainError(f"finish requires status=ACTIVE, got {self._status.value!r}")
        self._status = WorkflowStatus.COMPLETED
        self._change(now=now)
        self.append_event(WorkflowFinishedEvent.now(self._id, now))

    def fail(self, *, now: OccurredAt) -> None:
        if self._deleted_at.value is not None:
            raise DomainError("Workflow already deleted")
        if self._status != WorkflowStatus.ACTIVE:
            raise DomainError(f"fail requires status=ACTIVE, got {self._status.value!r}")
        self._status = WorkflowStatus.FAILED
        self._change(now=now)
        self.append_event(WorkflowFailedEvent.now(self._id, now))

    def abort(self, *, now: OccurredAt) -> None:
        if self._deleted_at.value is not None:
            raise DomainError("Workflow already deleted")
        if self._status != WorkflowStatus.ACTIVE:
            raise DomainError(f"abort requires status=ACTIVE, got {self._status.value!r}")
        self._status = WorkflowStatus.ABORTED
        self._change(now=now)
        self.append_event(WorkflowAbortedEvent.now(self._id, now))

    def pause(self, now: OccurredAt) -> None:
        if self._deleted_at.value is not None:
            raise DomainError("Workflow already deleted")
        if self._status != WorkflowStatus.ACTIVE:
            raise DomainError(f"pause requires status=ACTIVE, got {self._status.value!r}")
        self._status = WorkflowStatus.PAUSED
        self._change(now=now)
        self.append_event(WorkflowPausedEvent.now(self._id, now))

    def resume(self, now: OccurredAt) -> None:
        if self._deleted_at.value is not None:
            raise DomainError("Workflow already deleted")
        if self._status != WorkflowStatus.PAUSED:
            raise DomainError(f"resume requires status=PAUSED, got {self._status.value!r}")
        self._status = WorkflowStatus.ACTIVE
        self._change(now=now)
        self.append_event(WorkflowResumedEvent.now(self._id, now))

    def touch(self, now: OccurredAt) -> None:
        if self._deleted_at.value is not None:
            raise DomainError("Workflow already deleted")
        self._change(now=now)

    def delete(self, now: DeletedAt) -> None:
        if self._deleted_at.value is not None:
            raise DomainError("Workflow already deleted")
        self._delete(now)

    @classmethod
    def restore(
        cls,
        *,
        id: WorkflowId,
        created_at: CreatedAt,
        deleted_at: DeletedAt = NONE_DELETED_AT,
        changed_at: ChangedAt = NONE_CHANGED_AT,
        session_id: SessionIdRef,
        project_id: ProjectIdRef,
        status: WorkflowStatus,
    ) -> Self:
        workflow = cls(
            id=id,
            session_id=session_id,
            project_id=project_id,
            status=status,
            created_at=created_at,
            deleted_at=deleted_at,
        )
        workflow._changed_at = changed_at
        return workflow

    # --- Properties ---

    def _change(self, now: OccurredAt) -> None:
        self._changed_at = ChangedAt.from_datetime(now.value)
        self.append_event(
            WorkflowChangedEvent.now(
                workflow_id=self._id,
                now=OccurredAt.from_datetime(now.value),
            )
        )

    def _delete(self, now: DeletedAt) -> None:
        self._deleted_at = now
        self.append_event(
            WorkflowDeletedEvent.now(
                workflow_id=self._id,
                now=OccurredAt.from_datetime(now.value),
            )
        )

    @property
    def session_id(self) -> SessionIdRef:
        return self._session_id

    @property
    def project_id(self) -> ProjectIdRef:
        return self._project_id

    @property
    def status(self) -> WorkflowStatus:
        return self._status

    @property
    def created_at(self) -> CreatedAt:
        return self._created_at

    @property
    def changed_at(self) -> ChangedAt:
        return self._changed_at

    @property
    def deleted_at(self) -> DeletedAt:
        return self._deleted_at

    # --- Factory ---
