"""make_default_inputs_required

Revision ID: 7e32f815b489
Revises: 0002
Create Date: 2025-10-02 17:00:42.241765

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '7e32f815b489'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update any existing NULL values to empty JSON object
    op.execute(
        """
        UPDATE app_templates
        SET default_inputs = '{}'::jsonb
        WHERE default_inputs IS NULL
        """
    )

    # Make the column NOT NULL
    op.alter_column(
        'app_templates',
        'default_inputs',
        existing_type=postgresql.JSON(),
        nullable=False,
    )


def downgrade() -> None:
    # Make the column nullable again
    op.alter_column(
        'app_templates',
        'default_inputs',
        existing_type=postgresql.JSON(),
        nullable=True,
    )
