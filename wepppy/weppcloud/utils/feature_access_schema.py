"""Account metadata shared by Flask models and non-Flask feature decisions."""

import sqlalchemy as sa


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


metadata = sa.MetaData()
users = sa.Table("user", metadata, sa.Column("id", sa.Integer, primary_key=True), sa.Column("active", sa.Boolean))
roles = sa.Table("role", metadata, sa.Column("id", sa.Integer, primary_key=True), sa.Column("name", sa.String))
roles_users = sa.Table("roles_users", metadata, sa.Column("user_id", sa.Integer), sa.Column("role_id", sa.Integer))
groups, memberships, events, acceptances = feature_access_tables(metadata)
