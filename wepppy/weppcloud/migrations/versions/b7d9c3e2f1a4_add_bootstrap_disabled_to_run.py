"""Add bootstrap_disabled to Run

Revision ID: b7d9c3e2f1a4
Revises: cac20a11c2cb
Create Date: 2026-02-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b7d9c3e2f1a4"
down_revision = "cac20a11c2cb"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("run", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "bootstrap_disabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade():
    with op.batch_alter_table("run", schema=None) as batch_op:
        batch_op.drop_column("bootstrap_disabled")
