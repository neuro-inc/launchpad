"""

Add AppTemplate table

Revision ID: 0002
Revises: 0001
Create Date: 2025-09-30 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create app_templates table
    op.create_table(
        "app_templates",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("template_name", sa.String(), nullable=False),
        sa.Column("template_version", sa.String(), nullable=False),
        sa.Column("verbose_name", sa.String(), nullable=False),
        sa.Column("description_short", sa.String(), nullable=False),
        sa.Column("description_long", sa.String(), nullable=False),
        sa.Column("logo", sa.String(), nullable=False),
        sa.Column(
            "documentation_urls", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "external_urls", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("tags", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False),
        sa.Column("is_shared", sa.Boolean(), nullable=False),
        sa.Column("handler_class", sa.String(), nullable=True),
        sa.Column(
            "default_inputs",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
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
        sa.UniqueConstraint("name", name="unique__app_templates__name"),
    )
    op.create_index(
        op.f("ix_app_templates_name"),
        "app_templates",
        ["name"],
        unique=True,
    )


def downgrade() -> None:
    # Drop app_templates table
    op.drop_index(op.f("ix_app_templates_name"), table_name="app_templates")
    op.drop_table("app_templates")
