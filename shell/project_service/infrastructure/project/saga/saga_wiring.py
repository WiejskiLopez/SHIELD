"""Składanie UoW sagi w project_service. Jedyny plik infra sagi (obok result writer)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from saga_orchestration.domain.ports.outbox_writer import CommandOutboxWriter, OutboxCommandRow

from shell.platform.application.context.causation_id import set_causation_id
from shell.platform.application.context.correlation_id import set_correlation_id
from shell.platform.infrastructure.messaging.command.sql_command_outbox_writer import (
    SqlCommandOutboxWriter,
)
from shell.platform.infrastructure.process.saga.sql_saga_uow_factory import (
    build_sql_saga_unit_of_work_factory,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from saga_orchestration.domain.step import StepRegistry
    from saga_orchestration.infrastructure.sqlalchemy.saga_models import SagaModels
    from saga_orchestration.infrastructure.sqlalchemy.sql_saga_uow import SqlSagaUnitOfWork
    from sqlalchemy.ext.asyncio import AsyncSession

    from shell.platform.application.contracts.command_contract import CommandContract
    from shell.platform.infrastructure.persistence.sql.models.command_delivery import (
        CommandDeliveryModels,
    )


class ProjectCommandOutboxWriter(CommandOutboxWriter):
    """Wiersz libki -> command_outbox projektu na ZWIĄZANEJ sesji (bez commit).

    Ciągłość trace: correlation/causation z wiersza sagi ustawiane w kontekście
    przed delegacją, żeby relay poniósł dalej tożsamość sagi, nie procesora.
    """

    def __init__(
        self,
        session: AsyncSession,
        commands_models: CommandDeliveryModels,
        contracts: Mapping[str, CommandContract],
        source_service: str = "project",
    ) -> None:
        self._session = session
        self._writer = SqlCommandOutboxWriter(commands_models, source_service)
        self._contracts = dict(contracts)

    def append(self, row: OutboxCommandRow) -> None:
        contract = self._contracts.get(row.contract_type)
        if contract is None:
            raise ValueError(f"nieznany kontrakt sagi: {row.contract_type!r}")
        set_correlation_id(row.correlation_id)
        if row.causation_id is not None:
            set_causation_id(row.causation_id)
        self._writer.append(
            self._session,
            contract=contract,
            payload=dict[str, object](row.payload),
            command_id=row.command_id,
        )


def build_project_saga_unit_of_work_factory(
    *,
    session_factory: Callable[[], AsyncSession],
    models: SagaModels,
    commands_models: CommandDeliveryModels,
    contracts: Mapping[str, CommandContract],
    registries: Mapping[str, StepRegistry],
) -> Callable[[], SqlSagaUnitOfWork]:
    """Fabryka UoW sagi: sesja współdzielona ze scope albo własna (worker/start)."""

    return build_sql_saga_unit_of_work_factory(
        session_factory=session_factory,
        models=models,
        commands_models=commands_models,
        contracts=contracts,
        registries=registries,
        writer_factory=ProjectCommandOutboxWriter,
    )
