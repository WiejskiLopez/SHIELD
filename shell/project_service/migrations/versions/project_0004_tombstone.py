"""Reserve the removed ``project_0004`` revision in the migration chain.

The original migration was removed after databases may already have recorded
its revision. Keeping this no-op revision preserves a linear, downgradeable
history without changing the identity of later migrations.
"""

from __future__ import annotations

from alembic import op

revision = "project_0004_tombstone"
down_revision = "project_0003_project_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SELECT 1")


def downgrade() -> None:
    op.execute("SELECT 1")
