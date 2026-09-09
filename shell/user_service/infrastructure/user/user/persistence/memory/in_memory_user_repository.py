from __future__ import annotations

from shell.platform.infrastructure.persistence.in_memory_repository import InMemoryRepository
from shell.user_service.domain.user.aggregates.user.repositories.user_repository import (
    UserRepository,
)
from shell.user_service.domain.user.aggregates.user.user import User
from shell.user_service.domain.user.value_objects.user_id import UserId


class InMemoryUserRepository(InMemoryRepository[User, UserId], UserRepository):
    async def get_by_id(self, id: UserId) -> User | None:
        user = self._store.get(id.value)
        if user is None or user.deleted_at.value is not None:
            return None
        return user
