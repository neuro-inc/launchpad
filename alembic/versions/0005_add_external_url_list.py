"""

Add external_url_list to InstalledApp

Revision ID: 0005
Revises: 0004
Create Date: 2025-12-30 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "installed_apps",
        sa.Column(
            "external_url_list",
            postgresql.ARRAY(sa.String()),
            server_default="{}",
            nullable=False,
        ),
    )
    op.create_index(
        "ix_installed_apps_external_url_list",
        "installed_apps",
        ["external_url_list"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_installed_apps_external_url_list", table_name="installed_apps")
    op.drop_column("installed_apps", "external_url_list")
