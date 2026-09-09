"""Kontrakt repozytorium node_execution."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import String

from shell.execution_service.domain.execution.aggregates.node_execution.node_execution import (
    NodeExecution,
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
from shell.execution_service.infrastructure.execution.node_execution.persistence.sql.models.node_execution import (
    NodeExecutionModel,
)
from shell.platform.domain.value_objects.created_at import CreatedAt
from shell.platform.domain.value_objects.occurred_at import OccurredAt

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _node_db_row(node_id: str, position: int) -> NodeExecutionModel:

    return NodeExecutionModel(
        id=node_id,
        position=position,
        node_type="test",
        node_definition_id="definition-1",
        created_at=_NOW,
        status="PENDING",
    )


def _node_entity(node_id: str, position: int) -> NodeExecution:
    return NodeExecution.create(
        id=NodeExecutionId(node_id),
        node_definition_id=NodeDefinitionIdRef("definition-1"),
        node_position=NodePosition(position),
        node_type=NodeType("test"),
        now=CreatedAt.from_datetime(_NOW),
    )

async def _clean_sql(session_factory: async_sessionmaker) -> None:
    from sqlalchemy import delete

    async with session_factory() as session:
        await session.execute(
            delete(NodeExecutionModel).where(NodeExecutionModel.node_type == "test")
        )
        await session.commit()


    async def test_save_get_by_id_round_trip_preserves_state(
        self,
        session_factory: async_sessionmaker,
    ) -> None:
        """HIGH-04/MEDIUM-01: entity -> model -> DB -> model -> entity zachowuje stan."""
        from shell.execution_service.infrastructure.execution.node_execution.persistence.sql.repositories.sql_node_execution_repository import (
            SqlNodeExecutionRepository,
        )

        await _clean_sql(session_factory)
        node = _node_entity("roundtrip-1", 4)
        node.start(now=OccurredAt.from_datetime(_NOW))

        async with session_factory() as session:
            repo = SqlNodeExecutionRepository(session)
            await repo.save(node)
            await session.commit()

        async with session_factory() as session:
            repo = SqlNodeExecutionRepository(session)
            restored = await repo.get_by_id(NodeExecutionId("roundtrip-1"))
            assert restored is not None

        assert restored.id.value == node.id.value
        assert restored.node_position.value == node.node_position.value
        assert restored.node_type.value == node.node_type.value
        assert restored.status is node.status

    async def test_model_entity_round_trip_matches_sql_column(self) -> None:
        """HIGH-04: migracja i ORM ds. status zgodne — kolumna status 50 znaków."""
        from shell.execution_service.infrastructure.execution.node_execution.persistence.sql.mappers import (
            node_execution_entity_to_model,
        )
        from shell.execution_service.infrastructure.execution.node_execution.persistence.sql.models.node_execution import (
            NodeExecutionModel,
        )

        node = _node_entity("col-1", 1)
        model = node_execution_entity_to_model(node)

        assert isinstance(NodeExecutionModel.__table__.c.status.type, String)
        assert NodeExecutionModel.__table__.c.status.type.length == 50
        assert model.status == node.status.value
