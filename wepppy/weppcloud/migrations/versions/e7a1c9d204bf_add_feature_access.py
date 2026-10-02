"""Add feature groups and retained access/onboarding history; seed no users."""

from alembic import op
import sqlalchemy as sa

revision = "e7a1c9d204bf"
down_revision = "d30c91a7b802"
branch_labels = None
depends_on = None


def feature_access_tables(metadata):
    groups = sa.Table(
        "feature_access_group", metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.String(80), nullable=False, unique=True),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    memberships = sa.Table(
        "feature_access_membership", metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("group_id", sa.Integer, sa.ForeignKey("feature_access_group.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("review_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("group_id", "user_id", name="uq_feature_access_membership"),
    )
    # Identifiers are historical snapshots, intentionally not cascading FKs.
    events = sa.Table(
        "feature_access_event", metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("actor_id", sa.Integer, nullable=False),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("group_id", sa.Integer, nullable=False),
        sa.Column("group_key", sa.String(80), nullable=False),
        sa.Column("feature_scope", sa.JSON, nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("review_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("action IN ('add', 'remove')", name="ck_feature_access_event_action"),
        sa.CheckConstraint("length(trim(reason)) > 0", name="ck_feature_access_event_reason"),
    )
    acceptances = sa.Table(
        "onboarding_acceptance", metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("statement_kind", sa.String(32), nullable=False),
        sa.Column("statement_version", sa.String(80), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("decision_rule", sa.String(80)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "statement_kind", "statement_version", name="uq_onboarding_acceptance"),
        sa.CheckConstraint("statement_kind IN ('internal', 'poweruser')", name="ck_onboarding_acceptance_kind"),
        sa.CheckConstraint("length(trim(statement_version)) > 0", name="ck_onboarding_acceptance_version"),
    )
    return groups, memberships, events, acceptances



def upgrade():
    metadata = sa.MetaData()
    sa.Table("user", metadata, sa.Column("id", sa.Integer, primary_key=True))
    tables = feature_access_tables(metadata)
    for table in tables:
        table.create(op.get_bind())
    op.bulk_insert(tables[0], [
        {"key": key, "label": label, "active": True}
        for key, label in (
            ("openet_ts", "OpenET Time Series"),
            ("batch_runner", "Batch Runner"),
            ("culvert_runner", "Culvert Runner"),
            ("omni_contrasts", "Omni Contrasts"),
            ("path_ce", "Path CE"),
            ("ag_fields", "Agricultural Fields"),
        )
    ])


def downgrade():
    # Operational rollback disables consumers; never discard access history.
    raise RuntimeError("Feature access history is retained; roll back consumers without downgrading this schema")
