"""Add account roles and active status."""

import sqlalchemy as sa
from alembic import op

revision = "b6d4474d05ab"
down_revision = "903718b26e7a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "accounts",
        sa.Column("role", sa.String(16), nullable=False, server_default="USER"),
    )
    op.add_column(
        "accounts",
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_check_constraint("ck_accounts_role", "accounts", "role IN ('USER','ADMIN')")


def downgrade():
    op.drop_constraint("ck_accounts_role", "accounts", type_="check")
    op.drop_column("accounts", "active")
    op.drop_column("accounts", "role")
