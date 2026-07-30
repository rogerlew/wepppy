"""Add typed account preferences and merge the current migration heads."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c91f6b2a4d7e"
down_revision = ("7b3c068e7a1d", "b7d9c3e2f1a4")
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "unit_system",
            sa.String(length=16),
            nullable=False,
            server_default="config",
        ),
        sa.Column(
            "wbt_boundary_touch_behavior",
            sa.String(length=16),
            nullable=False,
            server_default="config",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "unit_system IN ('config', 'si', 'english')",
            name="ck_user_preferences_unit_system",
        ),
        sa.CheckConstraint(
            "wbt_boundary_touch_behavior IN ('config', 'warn', 'error')",
            name="ck_user_preferences_wbt_boundary_touch_behavior",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_user_preferences_user_id_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_user_preferences"),
    )


def downgrade():
    op.drop_table("user_preferences")
