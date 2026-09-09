"""Adopt saga tables from the saga-orchestration DDL (deterministic).

Zastępuje pilotową migrację adopcyjną sagi (wzorzec zgadywania zamiast tworzenia).
Tworzy saga_instance + saga_timeout + saga_processed_delivery z JEDYNEGO
źródła DDL (`saga_schema.upgrade_saga_schema` na modelach serwisu).

Bazy deweloperskie z tabelami ery pilota: reset (`reset_db=True` w baseline),
migracja nie zgaduje stanu (brak IF NOT EXISTS).
"""

from __future__ import annotations

from alembic import op
from saga_orchestration.infrastructure.sqlalchemy.saga_schema import (
    downgrade_saga_schema,
    upgrade_saga_schema,
)

from shell.project_service.infrastructure.project.persistence.sql.models.base import (
    SAGA_MODELS,
)

revision = "project_0005_saga_schema"
down_revision = "project_0004_tombstone"
branch_labels = None
depends_on = None


def upgrade() -> None:
    upgrade_saga_schema(op.get_bind(), SAGA_MODELS)


def downgrade() -> None:
    downgrade_saga_schema(op.get_bind(), SAGA_MODELS)
