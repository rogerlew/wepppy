"""Add oauth_account table for external identity links.

Revision ID: 4b48d5aa1ba9
Revises: 28e48afd0090
Create Date: 2025-02-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "4b48d5aa1ba9"
down_revision = "cac20a11c2cb"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "oauth_account",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_uid", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_type", sa.String(length=50), nullable=True),
        sa.Column("token_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider", "provider_uid", name="uq_oauth_account_provider_uid"
        ),
    )
    op.create_index(
        "ix_oauth_account_user_id", "oauth_account", ["user_id"], unique=False
    )


def downgrade():
    op.drop_index("ix_oauth_account_user_id", table_name="oauth_account")
    op.drop_table("oauth_account")
