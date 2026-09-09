"""SQL ORM model <-> domain entity mappers for User aggregate."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shell.user_service.domain.user.aggregates.user.user import User
    from shell.user_service.infrastructure.user.user.persistence.sql.models.user import UserModel


def user_change_model(model: UserModel, entity: User) -> None:
    model.email = entity.email.value
    model.status = entity.status.value
    if entity.created_at is None:
        raise ValueError("User.created_at is required for persistence")
    model.created_at = entity.created_at.value
    model.changed_at = entity.changed_at.value  # type: ignore[assignment]
    model.deleted_at = entity.deleted_at.value
