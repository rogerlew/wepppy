"""Add the rebuildable run catalog without reading project files."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "d30c91a7b802"
down_revision = "c91f6b2a4d7e"
branch_labels = None
depends_on = None


def upgrade():
    columns = [
        sa.Column("run_id", sa.Integer, primary_key=True),
        sa.Column("projection_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text),
        sa.Column("scenario", sa.Text),
        sa.Column("readonly", sa.Boolean),
        sa.Column("map_lng", sa.Float),
        sa.Column("map_lat", sa.Float),
        sa.Column("map_zoom", sa.Float),
        sa.Column("ttl_policy", sa.Text),
        sa.Column("ttl_deletion_at", sa.DateTime(timezone=True)),
        sa.Column("source_locator", sa.Text),
        sa.Column("source_versions", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("projection_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("dirty_revision", sa.BigInteger, nullable=False, server_default="1"),
        sa.Column("indexed_revision", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("last_error_code", sa.Text),
    ]
    for source in ("ron", "readonly", "ttl"):
        columns.append(sa.Column(source + "_state", sa.Text, nullable=False, server_default="pending"))
    for name in ("dirty_since", "invalidated_at", "next_attempt_at", "next_reconcile_at"):
        columns.append(sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    for name in ("last_attempt_at", "ron_observed_at", "readonly_observed_at", "ttl_observed_at",
                 "refreshed_at", "reconciled_at"):
        columns.append(sa.Column(name, sa.DateTime(timezone=True)))
    constraints = {
        "revisions": "indexed_revision >= 0 AND dirty_revision >= indexed_revision",
        "version": "projection_version > 0",
        "source_versions": "jsonb_typeof(source_versions) = 'object'",
        "ron_state": "ron_state IN ('pending','ready','missing','invalid','unreadable')",
        "readonly_state": "readonly_state IN ('pending','ready','unreadable')",
        "ttl_state": "ttl_state IN ('pending','ready','missing','invalid','unreadable')",
        "ttl_expiration": "ttl_deletion_at IS NULL OR ((ttl_policy = 'rolling_90d' AND ttl_state = 'ready') IS TRUE)",
        "map_center": "(map_lng IS NULL AND map_lat IS NULL) OR (map_lng IS NOT NULL AND map_lat IS NOT NULL AND map_lng > '-Infinity'::float8 AND map_lng < 'Infinity'::float8 AND map_lat > '-Infinity'::float8 AND map_lat < 'Infinity'::float8)",
        "map_zoom": "map_zoom IS NULL OR (map_zoom > '-Infinity'::float8 AND map_zoom < 'Infinity'::float8)",
    }
    op.create_table("run_catalog", *columns,
                    sa.ForeignKeyConstraint(["run_id"], ["run.id"], ondelete="CASCADE"),
                    *(sa.CheckConstraint(expression, name="ck_run_catalog_" + name)
                      for name, expression in constraints.items()))
    op.create_index("ix_run_catalog_dirty", "run_catalog",
                    ["next_attempt_at", "dirty_since", "run_id"],
                    postgresql_where=sa.text("dirty_revision > indexed_revision"))
    op.create_index("ix_run_catalog_reconcile", "run_catalog", ["next_reconcile_at", "run_id"])


def downgrade():
    op.drop_table("run_catalog")
