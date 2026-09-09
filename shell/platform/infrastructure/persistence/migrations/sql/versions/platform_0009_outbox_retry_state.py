"""Add retry state columns to the outbox tables (poison-row isolation for relays)."""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "platform_0009_outbox_retry_state"
down_revision = "platform_0008_audit_event_timezone"
branch_labels = None
depends_on = None

_OUTBOX_TABLES = ("event_outbox", "command_outbox")

_COLUMN_NAMES = (
    "status",
    "next_attempt_at",
    "lease_until",
    "claimed_by",
    "last_attempted_at",
    "retry_count",
    "error_code",
    "error_message",
    "failed_at",
)


def _retry_columns() -> list[sa.Column[Any]]:
    return [
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_by", sa.String(), nullable=True),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    for table_name in _OUTBOX_TABLES:
        for column in _retry_columns():
            op.add_column(table_name, column)
        op.create_index(
            f"ix_{table_name}_status_next_attempt",
            table_name,
            ["status", "next_attempt_at"],
        )


def downgrade() -> None:
    for table_name in _OUTBOX_TABLES:
        op.drop_index(f"ix_{table_name}_status_next_attempt", table_name=table_name)
        with op.batch_alter_table(table_name) as batch_op:
            for column_name in _COLUMN_NAMES:
                batch_op.drop_column(column_name)
