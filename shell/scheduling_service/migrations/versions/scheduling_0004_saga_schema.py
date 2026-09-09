"""Adopt saga tables from the saga-orchestration DDL (deterministic).

Tworzy saga_instance + saga_timeout + saga_processed_delivery z JEDYNEGO
źródła DDL (`saga_schema.upgrade_saga_schema` na modelach serwisu).
"""

from __future__ import annotations

from alembic import op
from saga_orchestration.infrastructure.sqlalchemy.saga_schema import (
    downgrade_saga_schema,
    upgrade_saga_schema,
)

from shell.scheduling_service.infrastructure.scheduling.persistence.sql.models.base import (
    SAGA_MODELS,
)

revision = "scheduling_0004_saga_schema"
down_revision = "scheduling_0003_scheduler_job"
branch_labels = None
depends_on = None


def upgrade() -> None:
    upgrade_saga_schema(op.get_bind(), SAGA_MODELS)


def downgrade() -> None:
    downgrade_saga_schema(op.get_bind(), SAGA_MODELS)
