"""Make audit event timestamps timezone-aware."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "platform_0008_audit_event_timezone"
down_revision = "platform_0007_worker_heartbeat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("audit_event") as batch_op:
        batch_op.alter_column(
            "occurred_at",
            existing_type=sa.DateTime(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("audit_event") as batch_op:
        batch_op.alter_column(
            "occurred_at",
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(),
            existing_nullable=False,
        )
