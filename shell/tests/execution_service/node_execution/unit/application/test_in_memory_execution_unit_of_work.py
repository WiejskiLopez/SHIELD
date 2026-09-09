from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from shell.execution_service.domain.execution.aggregates.graph_execution.value_objects.graph_execution_id import (
    GraphExecutionId,
)
from shell.execution_service.domain.execution.aggregates.node_execution.node_execution import (
    NodeExecution,
)
from shell.execution_service.domain.execution.aggregates.node_execution.repositories.node_execution_repository import (
    NodeExecutionRepository,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_definition_id_ref import (
    NodeDefinitionIdRef,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_execution_id import (
    NodeExecutionId,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_position import (
    NodePosition,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_type import (
    NodeType,
)
from shell.execution_service.domain.execution.aggregates.node_link_execution.node_link_execution import (
    NodeLinkExecution,
)
from shell.execution_service.domain.execution.aggregates.node_link_execution.repositories.node_link_execution_repository import (
    NodeLinkExecutionRepository,
)
from shell.execution_service.domain.execution.aggregates.node_link_execution.value_objects.node_link_execution_id import (
    NodeLinkExecutionId,
)
from shell.execution_service.infrastructure.execution.node_link_execution.persistence.memory.in_memory_node_link_execution_repository import (
    InMemoryNodeLinkExecutionRepository,
)
from shell.execution_service.infrastructure.execution.persistence.memory.unit_of_work import (
    InMemoryExecutionUnitOfWork,
)
from shell.platform.application.commands.command import Command
from shell.platform.application.contracts.command_contract import CommandContract
from shell.platform.domain.value_objects.created_at import CreatedAt
from shell.platform.domain.value_objects.deleted_at import DeletedAt

_NOW = CreatedAt.from_datetime(datetime(2024, 1, 1, tzinfo=UTC))


@dataclass(frozen=True, slots=True)
class SampleCommand(Command):
    value: str = "ok"


def _aggregates() -> tuple[NodeExecution, NodeLinkExecution]:
    node = NodeExecution.create(
        id=NodeExecutionId("node-1"),
        graph_execution_id=GraphExecutionId("graph-1"),
        node_definition_id=NodeDefinitionIdRef("definition-1"),
        node_position=NodePosition(1),
        node_type=NodeType("worker"),
        now=_NOW,
    )
    link = NodeLinkExecution.create(
        id_=NodeLinkExecutionId("link-1"),
        graph_execution_id=GraphExecutionId("graph-1"),
        node_execution_id=node.id,
        now=_NOW,
    )
    return node, link


async def test_two_aggregate_saves_commit_together() -> None:
    unit_of_work = InMemoryExecutionUnitOfWork()
    node, link = _aggregates()

    async with unit_of_work:
        await unit_of_work.save(NodeExecutionRepository, node)
        await unit_of_work.save(NodeLinkExecutionRepository, link)

    assert await unit_of_work.repository(NodeExecutionRepository).get_by_id(node.id) is node
    assert await unit_of_work.repository(NodeLinkExecutionRepository).get_by_id(link.id) is link


async def test_save_is_not_visible_before_commit() -> None:
    unit_of_work = InMemoryExecutionUnitOfWork()
    node, _ = _aggregates()

    async with unit_of_work:
        await unit_of_work.save(NodeExecutionRepository, node)
        assert await unit_of_work.repository(NodeExecutionRepository).get_by_id(node.id) is None

    assert await unit_of_work.repository(NodeExecutionRepository).get_by_id(node.id) is node


async def test_explicit_rollback_discards_pending_save_and_events() -> None:
    unit_of_work = InMemoryExecutionUnitOfWork()
    node, _ = _aggregates()

    async with unit_of_work:
        await unit_of_work.save(NodeExecutionRepository, node)
        assert unit_of_work.events
        assert unit_of_work.committed_events == []
        await unit_of_work.rollback()

    assert await unit_of_work.repository(NodeExecutionRepository).get_by_id(node.id) is None
    assert unit_of_work.events == []
    assert unit_of_work.committed_events == []


async def test_staged_command_becomes_committed_only_after_commit() -> None:
    unit_of_work = InMemoryExecutionUnitOfWork()
    contract = CommandContract(
        command_name="SampleCommand",
        command_class=SampleCommand,
        target_service="execution",
    )

    async with unit_of_work:
        unit_of_work.stage_commands([(contract, SampleCommand(command_id="command-1"))])
        assert unit_of_work.committed_commands == []

    assert len(unit_of_work.committed_commands) == 1
    assert unit_of_work.committed_commands[0][1].command_id == "command-1"


async def test_invalid_staged_event_and_command_are_rejected() -> None:
    unit_of_work = InMemoryExecutionUnitOfWork()
    contract = CommandContract(
        command_name="SampleCommand",
        command_class=SampleCommand,
        target_service="execution",
    )

    with pytest.raises(TypeError, match="DomainEvent"):
        unit_of_work.stage_events([object()])

    with pytest.raises(TypeError, match="does not match"):
        unit_of_work.stage_commands([(contract, object())])


async def test_save_many_commits_all_aggregates_and_events() -> None:
    unit_of_work = InMemoryExecutionUnitOfWork()
    node, link = _aggregates()

    async with unit_of_work:
        await unit_of_work.save_many(
            (
                (NodeExecutionRepository, node),
                (NodeLinkExecutionRepository, link),
            )
        )
        assert unit_of_work.committed_events == []

    assert await unit_of_work.repository(NodeExecutionRepository).get_by_id(node.id) is node
    assert await unit_of_work.repository(NodeLinkExecutionRepository).get_by_id(link.id) is link
    assert len(unit_of_work.committed_events) == 2


async def test_failed_commit_restores_existing_repository_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unit_of_work = InMemoryExecutionUnitOfWork()
    existing_node, link = _aggregates()
    existing_node_id = existing_node.id

    async with unit_of_work:
        await unit_of_work.save(NodeExecutionRepository, existing_node)

    replacement, _ = _aggregates()
    replacement._id = existing_node_id
    link_repository = unit_of_work.repository(InMemoryNodeLinkExecutionRepository)

    async def fail_save(_link: NodeLinkExecution) -> None:
        raise RuntimeError("link save failed")

    monkeypatch.setattr(link_repository, "save", fail_save)

    with pytest.raises(RuntimeError, match="link save failed"):
        async with unit_of_work:
            await unit_of_work.save(NodeExecutionRepository, replacement)
            await unit_of_work.save(NodeLinkExecutionRepository, link)

    restored = await unit_of_work.repository(NodeExecutionRepository).get_by_id(existing_node_id)
    assert restored is not None
    assert restored.id == existing_node.id
    assert restored is not replacement


async def test_second_save_failure_rolls_back_first_save(monkeypatch: pytest.MonkeyPatch) -> None:
    unit_of_work = InMemoryExecutionUnitOfWork()
    node, link = _aggregates()
    link_repository = unit_of_work.repository(InMemoryNodeLinkExecutionRepository)

    async def fail_save(_link: NodeLinkExecution) -> None:
        raise RuntimeError("link save failed")

    monkeypatch.setattr(link_repository, "save", fail_save)

    with pytest.raises(RuntimeError, match="link save failed"):
        async with unit_of_work:
            await unit_of_work.save(NodeExecutionRepository, node)
            await unit_of_work.save(NodeLinkExecutionRepository, link)

    assert await unit_of_work.repository(NodeExecutionRepository).get_by_id(node.id) is None
    assert await unit_of_work.repository(NodeLinkExecutionRepository).get_by_id(link.id) is None


async def test_domain_delete_is_saved_as_soft_delete() -> None:
    unit_of_work = InMemoryExecutionUnitOfWork()
    node, _ = _aggregates()
    node.delete(DeletedAt.from_datetime(datetime(2024, 1, 2, tzinfo=UTC)))

    async with unit_of_work:
        await unit_of_work.save(NodeExecutionRepository, node)

    repository = unit_of_work.repository(NodeExecutionRepository)
    assert repository._store[node.id.value].deleted_at.value is not None
    assert (await repository.exists(node.id)).value is False


async def test_repository_delete_is_hard_delete() -> None:
    unit_of_work = InMemoryExecutionUnitOfWork()
    node, _ = _aggregates()

    async with unit_of_work:
        await unit_of_work.save(NodeExecutionRepository, node)

    repository = unit_of_work.repository(NodeExecutionRepository)
    await repository.delete(node.id)

    assert node.id.value not in repository._store
