from __future__ import annotations

from typing import TYPE_CHECKING, Any

from shell.platform.infrastructure.persistence.sql_alchemy_uow_base import SqlAlchemyUnitOfWorkBase
from shell.user_service.domain.user.aggregates.user_state.repositories.user_state_repository import (
    UserStateRepository,
)
from shell.user_service.infrastructure.user.user_state.persistence.sql.repositories.sql_user_state_repository import (
    SqlUserStateRepository,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from shell.platform.infrastructure.persistence.sql.models.persistence_delivery import (
        PersistenceDeliveryModels,
    )

_REPO_MAP: dict[type, type] = {
    UserStateRepository: SqlUserStateRepository,
}


class SqlAlchemyUserStateUnitOfWork(SqlAlchemyUnitOfWorkBase):
    def __init__(
           self,
           session_factory: async_sessionmaker[AsyncSession],
           mapper: Any,
           source_service: str,
           models: PersistenceDeliveryModels,
    ) -> None:
           super().__init__(session_factory, mapper=mapper, source_service=source_service, models=models)

    def _build_repo_map(self) -> dict[type, type]:
        return _REPO_MAP
