from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from shell.execution_service.domain.execution.aggregates.graph_execution.events.graph_execution_created_event import (
    GraphExecutionCreatedEvent,
)
from shell.execution_service.domain.execution.aggregates.graph_execution.graph_execution import (
    GraphExecution,
)
from shell.execution_service.domain.execution.aggregates.graph_execution.value_objects.graph_depth import (
    GraphDepth,
)
from shell.execution_service.domain.execution.aggregates.graph_execution.value_objects.graph_execution_id import (
    GraphExecutionId,
)
from shell.execution_service.domain.execution.aggregates.graph_execution.value_objects.max_subgraph_depth import (
    MaxSubgraphDepth,
)
from shell.execution_service.domain.execution.aggregates.task_execution.value_objects.task_execution_id import (
    TaskExecutionId,
)
from shell.platform.domain.value_objects.created_at import CreatedAt

if TYPE_CHECKING:
    from shell.platform.domain.events import DomainEvent

_NOW_DT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_NOW = CreatedAt.from_datetime(_NOW_DT)


def _created_event(graph: GraphExecution) -> GraphExecutionCreatedEvent:
    events = graph.pull_events()
    assert len(events) == 1
    event: DomainEvent = events[0]
    assert isinstance(event, GraphExecutionCreatedEvent)
    return event


class TestGraphExecutionFactories:
    def test_create_main_round_emits_created_event(self) -> None:
        graph = GraphExecution.create_main_round(
            id_=GraphExecutionId.generate(),
            task_execution_id=TaskExecutionId("task-1"),
            depth=GraphDepth(0),
            max_subgraph_depth=MaxSubgraphDepth(5),
            now=_NOW,
        )
        event = _created_event(graph)
        assert event.graph_execution_id.value == graph.id.value

    def test_create_sub_graph_emits_created_event_with_parent(self) -> None:
        parent_id = GraphExecutionId("parent-1")
        graph = GraphExecution.create_sub_graph(
            id_=GraphExecutionId("child-1"),
            task_execution_id=TaskExecutionId("task-1"),
            parent_id=parent_id,
            parent_depth=GraphDepth(0),
            max_subgraph_depth=MaxSubgraphDepth(5),
            now=_NOW,
        )
        event = _created_event(graph)
        assert event.graph_execution_id.value == graph.id.value
        assert graph.depth.value == 1
