from __future__ import annotations

from typing import TYPE_CHECKING, Any

from shell.platform.infrastructure.persistence.sql_alchemy_uow_base import SqlAlchemyUnitOfWorkBase
from shell.user_service.domain.user.aggregates.user_skill.repositories.user_skill_repository import (
    UserSkillRepository,
)
from shell.user_service.infrastructure.user.user_skill.persistence.sql.repositories.sql_user_skill_repository import (
    SqlUserSkillRepository,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from shell.platform.infrastructure.persistence.sql.models.persistence_delivery import (
        PersistenceDeliveryModels,
    )

_REPO_MAP: dict[type, type] = {
    UserSkillRepository: SqlUserSkillRepository,
}


class SqlAlchemyUserSkillUnitOfWork(SqlAlchemyUnitOfWorkBase):
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
