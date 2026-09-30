"""Store nonce-bound login grants and host-only alias sessions."""

import sqlalchemy as sa

from alembic import op


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_alias_sessions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("launchpad_id", sa.UUID(), nullable=False),
        sa.Column("app_id", sa.UUID(), nullable=False),
        sa.Column("hostname", sa.String(), nullable=False),
        sa.Column("login_digest", sa.String(), nullable=False, unique=True),
        sa.Column("nonce_digest", sa.String(), nullable=False),
        sa.Column("grant_digest", sa.String(), unique=True),
        sa.Column("session_digest", sa.String(), unique=True),
        sa.Column("access_token", sa.String()),
        sa.Column("user_id", sa.String()),
        sa.Column("token_expires_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_auth_alias_sessions_expires_at", "auth_alias_sessions", ["expires_at"]
    )

    op.create_index(
        "ix_auth_alias_sessions_launchpad_id_user_id",
        "auth_alias_sessions",
        ["launchpad_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_table("auth_alias_sessions")
