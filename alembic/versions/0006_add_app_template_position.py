"""

Add position to app_templates

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-29 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "app_templates",
        sa.Column("position", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        WITH ranked_templates AS (
            SELECT
                id,
                row_number() OVER (ORDER BY created_at ASC, id ASC) - 1 AS position
            FROM app_templates
            WHERE is_internal IS FALSE
        )
        UPDATE app_templates AS template
        SET position = ranked_templates.position
        FROM ranked_templates
        WHERE template.id = ranked_templates.id
        """
    )
    op.create_unique_constraint(
        "unique__app_templates__position",
        "app_templates",
        ["position"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_check_constraint(
        "check__app_templates__position_visibility",
        "app_templates",
        "(is_internal AND position IS NULL) OR "
        "(NOT is_internal AND position IS NOT NULL AND position >= 0)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "check__app_templates__position_visibility",
        "app_templates",
        type_="check",
    )
    op.drop_constraint(
        "unique__app_templates__position",
        "app_templates",
        type_="unique",
    )
    op.drop_column("app_templates", "position")
