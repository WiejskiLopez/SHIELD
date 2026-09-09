from __future__ import annotations

from typing import TYPE_CHECKING, Any

from shell.ingestion_service.domain.ingestion.aggregates.ingestion.repositories.ingestion_repository import (
    IngestionRepository,
)
from shell.ingestion_service.infrastructure.ingestion.persistence.sql.repositories.sql_ingestion_repository import (
    SqlIngestionRepository,
)
from shell.platform.infrastructure.persistence.sql_alchemy_uow_base import SqlAlchemyUnitOfWorkBase

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from shell.platform.infrastructure.persistence.sql.models.persistence_delivery import (
        PersistenceDeliveryModels,
    )


class IngestionUnitOfWork(SqlAlchemyUnitOfWorkBase):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mapper: Any,
        source_service: str,
        models: PersistenceDeliveryModels,
    ) -> None:
        super().__init__(
            session_factory,
            mapper=mapper,
            source_service=source_service,
            models=models,
        )

    def _build_repo_map(self) -> dict[type, type]:
        return {IngestionRepository: SqlIngestionRepository}
