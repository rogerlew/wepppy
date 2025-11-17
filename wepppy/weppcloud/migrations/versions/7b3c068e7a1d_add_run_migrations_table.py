"""Add run_migrations table for run sync provenance."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "7b3c068e7a1d"
down_revision = "4b48d5aa1ba9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "run_migrations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("runid", sa.String(length=255), nullable=False),
        sa.Column("config", sa.String(length=255), nullable=False),
        sa.Column("local_path", sa.String(length=1024), nullable=False),
        sa.Column("source_host", sa.String(length=255), nullable=True),
        sa.Column("original_url", sa.String(length=1024), nullable=True),
        sa.Column("pulled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_email", sa.String(length=255), nullable=True),
        sa.Column("version_at_pull", sa.Integer(), nullable=True),
        sa.Column("traits_detected", sa.JSON(), nullable=True),
        sa.Column("last_migration_version", sa.Integer(), nullable=True),
        sa.Column("last_status", sa.String(length=64), nullable=True),
        sa.Column("archive_before", sa.String(length=255), nullable=True),
        sa.Column("archive_after", sa.String(length=255), nullable=True),
        sa.Column("is_fixture", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("runid", "config", name="uq_run_migrations_runid_config"),
    )
    op.create_index(
        "ix_run_migrations_runid_config",
        "run_migrations",
        ["runid", "config"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_run_migrations_runid_config", table_name="run_migrations")
    op.drop_table("run_migrations")
