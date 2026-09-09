from __future__ import annotations

from datetime import UTC, datetime

import pytest

from shell.execution_service.domain.execution.aggregates.graph_execution.value_objects.graph_execution_id import (
    GraphExecutionId,
)
from shell.execution_service.domain.execution.aggregates.node_execution.exceptions.invalid_node_state_error import (
    InvalidNodeStateError,
)
from shell.execution_service.domain.execution.aggregates.node_execution.node_execution import (
    NodeExecution,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_definition_id_ref import (
    NodeDefinitionIdRef,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_execution_id import (
    NodeExecutionId,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_execution_status import (
    NodeExecutionStatus,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_position import (
    NodePosition,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_type import (
    NodeType,
)
from shell.platform.domain.value_objects.created_at import CreatedAt
from shell.platform.domain.value_objects.occurred_at import OccurredAt

_NOW_DT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_NOW = CreatedAt.from_datetime(_NOW_DT)
_OCCURRED = OccurredAt.from_datetime(_NOW_DT)


def _node() -> NodeExecution:
    node = NodeExecution.create(
        id=NodeExecutionId.generate(),
        node_definition_id=NodeDefinitionIdRef("definition-1"),
        node_type=NodeType("agent"),
        graph_execution_id=GraphExecutionId("graph-1"),
        node_position=NodePosition(0),
        now=_NOW,
    )
    node.pull_events()
    return node


def _assert_transition_events(node: NodeExecution, intent_event_name: str) -> None:
    events = node.pull_events()
    assert len(events) == 2
    assert type(events[0]).__name__ == "NodeExecutionChangedEvent"
    assert type(events[1]).__name__ == intent_event_name


class TestNodeExecutionFsm:
    def test_start_emits_changed_event(self) -> None:
        node = _node()
        node.start(now=_OCCURRED)
        assert node.status == NodeExecutionStatus.RUNNING
        assert node.changed_at.value == _NOW_DT
        _assert_transition_events(node, "NodeExecutionStartedEvent")

    def test_complete_emits_changed_event(self) -> None:
        node = _node()
        node.start(now=_OCCURRED)
        node.pull_events()
        node.complete(now=_OCCURRED)
        assert node.status == NodeExecutionStatus.COMPLETED
        _assert_transition_events(node, "NodeExecutionCompletedEvent")

    def test_fail_emits_changed_event(self) -> None:
        node = _node()
        node.start(now=_OCCURRED)
        node.pull_events()
        node.fail(now=_OCCURRED)
        assert node.status == NodeExecutionStatus.FAILED
        _assert_transition_events(node, "NodeExecutionFailedEvent")

    def test_timeout_emits_changed_event(self) -> None:
        node = _node()
        node.start(now=_OCCURRED)
        node.pull_events()
        node.timeout(now=_OCCURRED)
        assert node.status == NodeExecutionStatus.TIMED_OUT
        _assert_transition_events(node, "NodeExecutionTimedOutEvent")

    def test_retry_emits_changed_event(self) -> None:
        node = _node()
        node.start(now=_OCCURRED)
        node.pull_events()
        node.fail(now=_OCCURRED)
        node.pull_events()
        node.retry(now=_OCCURRED)
        assert node.status == NodeExecutionStatus.PENDING
        _assert_transition_events(node, "NodeExecutionRetriedEvent")

    def test_invalid_transition_raises_and_emits_no_event(self) -> None:
        node = _node()
        node.pull_events()
        with pytest.raises(InvalidNodeStateError):
            node.complete(now=_OCCURRED)
        assert node.pull_events() == []

    def test_start_on_completed_raises_and_emits_no_event(self) -> None:
        node = _node()
        node.start(now=_OCCURRED)
        node.pull_events()
        node.complete(now=_OCCURRED)
        node.pull_events()
        with pytest.raises(InvalidNodeStateError):
            node.start(now=_OCCURRED)
        assert node.pull_events() == []
