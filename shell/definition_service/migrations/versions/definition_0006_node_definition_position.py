"""Add the node position to node definitions."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "definition_0006_node_definition_position"
down_revision = "definition_0005_node_link_definition"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "node_definition",
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("node_definition", "position")