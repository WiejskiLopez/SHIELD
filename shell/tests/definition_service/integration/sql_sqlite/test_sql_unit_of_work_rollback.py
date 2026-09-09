"""SQLite integration tests — verifies SQL repositories and UnitOfWork via application handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from shell.definition_service.application.definition.runner_config.queries.get_runner_config_by_id_query import (
    GetRunnerConfigByIdQuery,
)
from shell.definition_service.application.definition.runner_config.query_handlers.get_runner_config_by_id_handler import (
    GetRunnerConfigByIdHandler,
)
from shell.definition_service.domain.definition.aggregates.runner_config.events.runner_config_created_event import (
    RunnerConfigCreatedEvent,
)
from shell.definition_service.domain.definition.aggregates.runner_config.repositories.runner_config_repository import (
    RunnerConfigRepository,
)
from shell.definition_service.domain.definition.aggregates.runner_config.runner_config import (
    RunnerConfig,
)
from shell.definition_service.domain.definition.aggregates.runner_config.value_objects.runner_config_id import (
    RunnerConfigId,
)
from shell.definition_service.infrastructure.definition.persistence.sql.models.base import (
    PERSISTENCE_DELIVERY_MODELS,
)
from shell.definition_service.infrastructure.definition.runner_config.persistence.sql.services.runner_config_query_service import (
    RunnerConfigQueryService as SqlRunnerConfigQueryService,
)
from shell.platform.application.commands.command import Command
from shell.platform.application.contracts.command_contract import CommandContract
from shell.platform.domain.value_objects.created_at import CreatedAt
from shell.platform.domain.value_objects.occurred_at import OccurredAt

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from shell.definition_service.infrastructure.definition.runner_config.persistence.sql.unit_of_work import (
        SqlAlchemyRunnerConfigUnitOfWork,
    )
    from shell.platform.infrastructure.persistence.memory import FakeClock


@dataclass(frozen=True, slots=True)
class SampleCommand(Command):
    value: str = "ok"


class TestSqlUnitOfWorkRollback:
    async def test_context_exit_auto_commits_staged_event_outbox(
        self,
        sql_uow: SqlAlchemyRunnerConfigUnitOfWork,
        session_factory: async_sessionmaker,
        clock: FakeClock,
    ) -> None:
        event = RunnerConfigCreatedEvent.now(
            runner_config_id=RunnerConfigId("commit-runner-x"),
            now=OccurredAt.from_datetime(clock.now()),
        )

        async with sql_uow as unit_of_work:
            unit_of_work.stage_events([event])
            assert unit_of_work.events

            async with session_factory() as separate_session:
                assert (
                    await separate_session.get(
                        PERSISTENCE_DELIVERY_MODELS.events.outbox,
                        "commit-runner-x",
                    )
                ) is None

        async with session_factory() as session:
            event_rows = (
                (await session.execute(select(PERSISTENCE_DELIVERY_MODELS.events.outbox)))
                .scalars()
                .all()
            )
            audit_rows = (
                (await session.execute(select(PERSISTENCE_DELIVERY_MODELS.audit)))
                .scalars()
                .all()
            )

        assert len([row for row in event_rows if row.aggregate_id == event.aggregate_id.value]) == 1
        assert len(
            [
                row
                for row in audit_rows
                if row.integration_event_name == "RunnerConfigCreatedIntegrationEvent"
            ]
        ) == 1

    async def test_save_many_commits_all_business_changes_and_events(
        self,
        sql_uow: SqlAlchemyRunnerConfigUnitOfWork,
        session_factory: async_sessionmaker,
        clock: FakeClock,
    ) -> None:
        events = tuple(
            RunnerConfigCreatedEvent.now(
                runner_config_id=RunnerConfigId(f"save-many-runner-{index}"),
                now=OccurredAt.from_datetime(clock.now()),
            )
            for index in (1, 2)
        )

        async with sql_uow as unit_of_work:
            unit_of_work.stage_events(events)

        async with session_factory() as session:
            event_rows = (
                (await session.execute(select(PERSISTENCE_DELIVERY_MODELS.events.outbox)))
                .scalars()
                .all()
            )

        aggregate_ids = {row.aggregate_id for row in event_rows}
        assert {event.aggregate_id.value for event in events} <= aggregate_ids

    async def test_command_outbox_is_rolled_back_with_business_transaction(
        self,
        sql_uow: SqlAlchemyRunnerConfigUnitOfWork,
        session_factory: async_sessionmaker,
    ) -> None:
        with pytest.raises(RuntimeError, match="forced command rollback"):
            async with sql_uow as unit_of_work:
                unit_of_work.stage_commands(
                    [
                        (
                            CommandContract(
                                command_name="SampleCommand",
                                command_class=SampleCommand,
                                target_service="execution",
                            ),
                            SampleCommand(command_id="rollback-command-1"),
                        )
                    ]
                )
                raise RuntimeError("forced command rollback")

        async with session_factory() as session:
            row = (
                await session.execute(
                    select(PERSISTENCE_DELIVERY_MODELS.commands.outbox).where(
                        PERSISTENCE_DELIVERY_MODELS.commands.outbox.command_id
                        == "rollback-command-1"
                    )
                )
            ).scalar_one_or_none()

        assert row is None

    async def test_repeated_commit_does_not_duplicate_staged_command(
        self,
        sql_uow: SqlAlchemyRunnerConfigUnitOfWork,
        session_factory: async_sessionmaker,
    ) -> None:
        async with sql_uow as unit_of_work:
            unit_of_work.stage_commands(
                [
                    (
                        CommandContract(
                            command_name="SampleCommand",
                            command_class=SampleCommand,
                            target_service="execution",
                        ),
                        SampleCommand(command_id="repeated-command-1"),
                    )
                ]
            )
            await unit_of_work.commit()
            await unit_of_work.commit()

        async with session_factory() as session:
            rows = (
                (
                    await session.execute(
                        select(PERSISTENCE_DELIVERY_MODELS.commands.outbox).where(
                            PERSISTENCE_DELIVERY_MODELS.commands.outbox.command_id
                            == "repeated-command-1"
                        )
                    )
                )
                .scalars()
                .all()
            )

        assert len(rows) == 1

    async def test_staged_command_is_written_to_command_outbox(
        self,
        sql_uow: SqlAlchemyRunnerConfigUnitOfWork,
        session_factory: async_sessionmaker,
    ) -> None:
        async with sql_uow as unit_of_work:
            unit_of_work.stage_commands(
                [
                    (
                        CommandContract(
                            command_name="SampleCommand",
                            command_class=SampleCommand,
                            target_service="execution",
                        ),
                        SampleCommand(command_id="staged-command-1"),
                    )
                ]
            )

        async with session_factory() as session:
            rows = (
                (
                    await session.execute(
                        select(PERSISTENCE_DELIVERY_MODELS.commands.outbox).where(
                            PERSISTENCE_DELIVERY_MODELS.commands.outbox.command_id
                            == "staged-command-1"
                        )
                    )
                )
                .scalars()
                .all()
            )

        assert len(rows) == 1
        assert rows[0].source_service == "definition_service"
        assert rows[0].target_service == "execution"

    async def test_rollback_on_exception_leaves_db_clean(
        self,
        sql_uow: SqlAlchemyRunnerConfigUnitOfWork,
        clock: FakeClock,
        session_factory: async_sessionmaker,
    ) -> None:
        try:
            async with sql_uow as u:
                await u.repository(RunnerConfigRepository).save(
                    RunnerConfig.create(
                        id_=RunnerConfigId("rollback-runner-x"),
                        now=CreatedAt.from_datetime(clock.now()),
                    )
                )
                raise RuntimeError("forced rollback")
        except RuntimeError:
            pass

        q = GetRunnerConfigByIdHandler(SqlRunnerConfigQueryService(session_factory))
        dto = await q.handle(GetRunnerConfigByIdQuery("rollback-runner-x"))
        assert dto is None

    async def test_context_exit_does_not_auto_commit_after_explicit_rollback(
        self,
        sql_uow: SqlAlchemyRunnerConfigUnitOfWork,
        session_factory: async_sessionmaker,
        clock: FakeClock,
    ) -> None:
        async with sql_uow as unit_of_work:
            await unit_of_work.repository(RunnerConfigRepository).save(
                RunnerConfig.create(
                    id_=RunnerConfigId("explicit-rollback-runner"),
                    now=CreatedAt.from_datetime(clock.now()),
                )
            )
            await unit_of_work.rollback()

        q = GetRunnerConfigByIdHandler(SqlRunnerConfigQueryService(session_factory))
        dto = await q.handle(GetRunnerConfigByIdQuery("explicit-rollback-runner"))
        assert dto is None
