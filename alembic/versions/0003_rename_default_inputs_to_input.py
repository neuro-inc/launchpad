"""

Rename default_inputs to input in app_templates table

Revision ID: 0003
Revises: 0002
Create Date: 2025-10-15 00:00:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename column from default_inputs to input
    op.alter_column(
        "app_templates",
        "default_inputs",
        new_column_name="input",
    )


def downgrade() -> None:
    # Rename column back from input to default_inputs
    op.alter_column(
        "app_templates",
        "input",
        new_column_name="default_inputs",
    )
