from __future__ import annotations

from typing import TYPE_CHECKING

from saga_orchestration.infrastructure.sqlalchemy.sql_saga_uow import SqlSagaUnitOfWork
from sqlalchemy.ext.asyncio import AsyncSession

from shell.platform.application.context.session_scope import get_session_scope

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from saga_orchestration.domain.ports.outbox_writer import CommandOutboxWriter
    from saga_orchestration.domain.step import StepRegistry
    from saga_orchestration.infrastructure.sqlalchemy.saga_models import SagaModels

    from shell.platform.application.contracts.command_contract import CommandContract
    from shell.platform.infrastructure.persistence.sql.models.command_delivery import (
        CommandDeliveryModels,
    )


def build_sql_saga_unit_of_work_factory(
    *,
    session_factory: Callable[[], AsyncSession],
    models: SagaModels,
    commands_models: CommandDeliveryModels,
    contracts: Mapping[str, CommandContract],
    registries: Mapping[str, StepRegistry],
    writer_factory: Callable[
        [AsyncSession, CommandDeliveryModels, Mapping[str, CommandContract]],
        CommandOutboxWriter,
    ],
) -> Callable[[], SqlSagaUnitOfWork]:
    """Builds a saga UoW using the current request session when available."""

    def factory() -> SqlSagaUnitOfWork:
        scope = get_session_scope()
        if scope is not None and scope.session is not None:
            session = scope.session
            if not isinstance(session, AsyncSession):
                raise TypeError(f"saga wymaga AsyncSession, jest {type(session).__name__}")
            owns_session = False
        else:
            session = session_factory()
            owns_session = True
        writer = writer_factory(session, commands_models, contracts)
        return SqlSagaUnitOfWork(session, models, writer, registries, owns_session=owns_session)

    return factory