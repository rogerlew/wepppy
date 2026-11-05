"""Notification tables; importing metadata does not initialize Flask."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


def notification_tables(metadata):
    notices = sa.Table(
        "notification", metadata,
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("kind", sa.String(80), nullable=False),
        sa.Column("source_key", sa.String(255), nullable=False, unique=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.Column("state", sa.String(16), nullable=False, server_default="active"),
        sa.Column("subject_type", sa.String(32)),
        # Intentionally not a foreign key: deletion must retain private inbox history.
        sa.Column("subject_id", sa.Integer),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.CheckConstraint("state IN ('active','unavailable','resolved')", name="ck_notification_state"),
        sa.CheckConstraint("jsonb_typeof(metadata) = 'object'", name="ck_notification_metadata"),
    )
    sa.Index("ix_notification_subject", notices.c.subject_type, notices.c.subject_id)
    sa.Index("uq_notification_live_subject", notices.c.kind, notices.c.subject_type,
             notices.c.subject_id, unique=True,
             postgresql_where=sa.text("state <> 'resolved' AND subject_id IS NOT NULL"))
    recipients = sa.Table(
        "notification_recipient", metadata,
        sa.Column("notification_id", sa.BigInteger,
                  sa.ForeignKey("notification.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("read_at", sa.DateTime(timezone=True)),
    )
    sa.Index("ix_notification_recipient_user_read", recipients.c.user_id,
             recipients.c.read_at, recipients.c.notification_id)
    return notices, recipients


metadata = sa.MetaData()
users = sa.Table("user", metadata, sa.Column("id", sa.Integer, primary_key=True))
runs = sa.Table("run", metadata, sa.Column("id", sa.Integer, primary_key=True),
                sa.Column("runid", sa.String(255)), sa.Column("config", sa.String(255)))
memberships = sa.Table("runs_users", metadata,
                       sa.Column("user_id", sa.Integer, primary_key=True),
                       sa.Column("run_id", sa.Integer, primary_key=True))
notifications, recipients = notification_tables(metadata)
