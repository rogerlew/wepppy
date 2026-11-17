"""Separate CILogon contact identity and local mailbox/credential provenance."""
from alembic import op
import sqlalchemy as sa

revision = "a7c1106e42b9"
down_revision = "f6b8d27a901c"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    duplicate = bind.execute(sa.text(
        'SELECT 1 FROM "user" WHERE email IS NOT NULL '
        'GROUP BY lower(trim(email)) HAVING count(*) > 1 LIMIT 1'
    )).first()
    if duplicate:
        raise RuntimeError("Duplicate normalized login emails require operator resolution before migration")
    for column in (
        sa.Column("account_kind", sa.String(16), nullable=False, server_default="shared"),
        sa.Column("contact_email", sa.String(255)),
        sa.Column("local_credential_state", sa.String(16), nullable=False, server_default="legacy"),
        sa.Column("mailbox_verified_email", sa.String(255)),
        sa.Column("mailbox_verified_at", sa.DateTime(timezone=True)),
        sa.Column("verification_nonce", sa.String(64)),
        sa.Column("verification_sent_at", sa.DateTime(timezone=True)),
    ):
        op.add_column("user", column)
    op.create_index("uq_user_normalized_login_email", "user", [sa.text("lower(trim(email))")], unique=True)


def downgrade():
    if op.get_bind().execute(sa.text(
        "SELECT 1 FROM \"user\" WHERE account_kind <> 'shared' "
        "OR local_credential_state <> 'legacy' OR mailbox_verified_at IS NOT NULL LIMIT 1"
    )).first():
        raise RuntimeError("Account state requires a compatible rollback; refusing destructive downgrade")
    op.drop_index("uq_user_normalized_login_email", table_name="user")
    for name in ("verification_sent_at", "verification_nonce", "mailbox_verified_at",
                 "mailbox_verified_email", "local_credential_state", "contact_email", "account_kind"):
        op.drop_column("user", name)
