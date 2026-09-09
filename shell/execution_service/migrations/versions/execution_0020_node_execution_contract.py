"""Align node_execution persistence with the NodeExecution aggregate."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "execution_0020_node_execution_contract"
down_revision = "execution_0019_node_link_execution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("node_execution") as batch_op:
        batch_op.add_column(sa.Column("node_definition_id", sa.String(), nullable=False))
        batch_op.add_column(sa.Column("changed_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
        for column_name in (
            "model",
            "command",
            "retries",
            "log_level",
            "max_step",
            "no_ask_user",
            "autopilot",
            "task_execution_id",
            "source_dir",
            "status_initial",
        ):
            batch_op.drop_column(column_name)


def downgrade() -> None:
    with op.batch_alter_table("node_execution") as batch_op:
        batch_op.add_column(sa.Column("model", sa.String(), nullable=False, server_default=""))
        batch_op.add_column(
            sa.Column("command", sa.String(), nullable=False, server_default="")
        )
        batch_op.add_column(sa.Column("retries", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(
            sa.Column("log_level", sa.String(), nullable=False, server_default="INFO")
        )
        batch_op.add_column(sa.Column("max_step", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(
            sa.Column("no_ask_user", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("autopilot", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("task_execution_id", sa.String(), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column("source_dir", sa.String(), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column("status_initial", sa.String(), nullable=False, server_default="")
        )
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("changed_at")
        batch_op.drop_column("node_definition_id")
