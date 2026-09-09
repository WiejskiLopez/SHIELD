from __future__ import annotations

from datetime import UTC, datetime

import pytest

from shell.execution_service.domain.execution.aggregates.task_execution.exceptions.invalid_task_state_error import (
    InvalidTaskStateError,
)
from shell.execution_service.domain.execution.aggregates.task_execution.task_execution import (
    TaskExecution,
)
from shell.execution_service.domain.execution.aggregates.task_execution.value_objects.task_execution_id import (
    TaskExecutionId,
)
from shell.execution_service.domain.execution.aggregates.task_execution.value_objects.task_execution_status import (
    TaskExecutionStatus,
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
from shell.platform.domain.value_objects.created_at import CreatedAt
from shell.platform.domain.value_objects.occurred_at import OccurredAt
from shell.platform.domain.value_objects.reason import Reason

_NOW_DT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_NOW = CreatedAt.from_datetime(_NOW_DT)
_OCCURRED = OccurredAt.from_datetime(_NOW_DT)


def _task() -> TaskExecution:
    task = TaskExecution.create(
        id_=TaskExecutionId.generate(),
        name=TaskName("my-task"),
        now=_NOW,
        workflow_id=WorkflowId("wf-1"),
        work_dir=WorkDir("workdir/sample"),
    )
    task.pull_events()
    return task


def _assert_transition_events(task: TaskExecution, intent_event_name: str) -> None:
    events = task.pull_events()
    assert len(events) == 2
    assert type(events[0]).__name__ == "TaskExecutionChangedEvent"
    assert type(events[1]).__name__ == intent_event_name


class TestTaskExecutionFsm:
    def test_start_emits_changed_event(self) -> None:
        task = _task()
        task.start(now=_OCCURRED)
        assert task.status == TaskExecutionStatus.IN_PROGRESS
        _assert_transition_events(task, "TaskExecutionStartedEvent")

    def test_complete_emits_changed_event(self) -> None:
        task = _task()
        task.start(now=_OCCURRED)
        task.pull_events()
        task.complete(now=_OCCURRED)
        assert task.status == TaskExecutionStatus.COMPLETED
        _assert_transition_events(task, "TaskExecutionCompletedEvent")

    def test_fail_emits_changed_event(self) -> None:
        task = _task()
        task.start(now=_OCCURRED)
        task.pull_events()
        task.fail(reason=Reason("boom"), now=_OCCURRED)
        assert task.status == TaskExecutionStatus.FAILED
        _assert_transition_events(task, "TaskExecutionFailedEvent")

    def test_timeout_emits_changed_event(self) -> None:
        task = _task()
        task.start(now=_OCCURRED)
        task.pull_events()
        task.timeout(now=_OCCURRED)
        assert task.status == TaskExecutionStatus.TIMED_OUT
        _assert_transition_events(task, "TaskExecutionTimedOutEvent")

    def test_exhaust_emits_changed_event(self) -> None:
        task = _task()
        task.start(now=_OCCURRED)
        task.pull_events()
        task.exhaust(now=_OCCURRED)
        assert task.status == TaskExecutionStatus.EXHAUSTED
        _assert_transition_events(task, "TaskExecutionExhaustedEvent")

    def test_rename_emits_changed_event(self) -> None:
        task = _task()
        task.pull_events()
        task.rename(new_name=TaskName("renamed"), now=_OCCURRED)
        assert task.name.value == "renamed"
        _assert_transition_events(task, "TaskExecutionRenamedEvent")

    def test_invalid_transition_raises_and_emits_no_event(self) -> None:
        task = _task()
        task.pull_events()
        with pytest.raises(InvalidTaskStateError):
            task.complete(now=_OCCURRED)
        assert task.pull_events() == []
