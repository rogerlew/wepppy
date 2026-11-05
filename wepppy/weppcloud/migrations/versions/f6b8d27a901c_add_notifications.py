"""Add account notification content and durable per-recipient read state."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "f6b8d27a901c"
down_revision = "e7a1c9d204bf"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notification",
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
        sa.Column("subject_id", sa.Integer),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.CheckConstraint("state IN ('active','unavailable','resolved')", name="ck_notification_state"),
        sa.CheckConstraint("jsonb_typeof(metadata) = 'object'", name="ck_notification_metadata"),
    )
    op.create_index("ix_notification_subject", "notification", ["subject_type", "subject_id"])
    op.create_index("uq_notification_live_subject", "notification", ["kind", "subject_type", "subject_id"],
                    unique=True, postgresql_where=sa.text("state <> 'resolved' AND subject_id IS NOT NULL"))
    op.create_table(
        "notification_recipient",
        sa.Column("notification_id", sa.BigInteger, sa.ForeignKey("notification.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("read_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_notification_recipient_user_read", "notification_recipient", ["user_id", "read_at", "notification_id"])


def downgrade():
    op.drop_table("notification_recipient")
    op.drop_table("notification")
