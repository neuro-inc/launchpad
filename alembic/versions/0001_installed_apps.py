"""

Installed Apps

Revision ID: 0001
Revises:
Create Date: 2025-07-25 12:16:58.678455

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "installed_apps",
        sa.Column("app_id", sa.UUID(), nullable=False),
        sa.Column("app_name", sa.String(), nullable=False),
        sa.Column("launchpad_app_name", sa.String(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False),
        sa.Column("is_shared", sa.Boolean(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "app_id",
            name="unique__installed_apps__launchpad_app_name__user_id",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index(
        op.f("ix_installed_apps_launchpad_app_name"),
        "installed_apps",
        ["launchpad_app_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_installed_apps_launchpad_app_name"), table_name="installed_apps"
    )
    op.drop_table("installed_apps")
