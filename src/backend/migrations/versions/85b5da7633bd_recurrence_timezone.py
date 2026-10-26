"""Preserve the recurrence schedule's local timezone."""

import sqlalchemy as sa
from alembic import op

revision = "85b5da7633bd"
down_revision = "6fca594817ed"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "recurrences", sa.Column("timezone", sa.String(80), nullable=False, server_default="UTC")
    )


def downgrade():
    op.drop_column("recurrences", "timezone")
