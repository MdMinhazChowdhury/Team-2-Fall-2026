"""Durable account-scoped export jobs."""

import sqlalchemy as sa
from alembic import op

revision = "903718b26e7a"
down_revision = "85b5da7633bd"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "export_jobs",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(as_uuid=False),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(40), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_export_jobs_account_id", "export_jobs", ["account_id"])
    op.create_index("ix_export_jobs_status", "export_jobs", ["status"])


def downgrade():
    op.drop_table("export_jobs")
