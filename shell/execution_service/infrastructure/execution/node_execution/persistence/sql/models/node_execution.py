from __future__ import annotations

from datetime import datetime  # noqa: TC003 - SQLAlchemy resolves Mapped[...] at class definition

from sqlalchemy import String
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from shell.execution_service.infrastructure.execution.persistence.sql.models.base import (
    ExecutionSqlAlchemyModelBase,
)
from shell.platform.infrastructure.persistence.sql.models.mixins import VersionedMixin


class NodeExecutionModel(ExecutionSqlAlchemyModelBase, VersionedMixin):
    __tablename__ = "node_execution"

    id: Mapped[str] = mapped_column(primary_key=True)
    position: Mapped[int] = mapped_column(nullable=False, default=0)
    node_type: Mapped[str] = mapped_column(nullable=False, default="")
    node_definition_id: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    changed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)

    @declared_attr  # type: ignore[arg-type]
    def __mapper_args__(cls) -> dict[str, object]:
        return {"version_id_col": cls.version}
