"""

Change app_templates uniqueness constraint to composite (name, template_name, template_version)

Revision ID: 0004
Revises: 0003
Create Date: 2025-10-17 00:00:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the existing unique index on name
    op.drop_index("ix_app_templates_name", table_name="app_templates")

    # Drop the old unique constraints
    op.drop_constraint("unique__app_templates__name", "app_templates", type_="unique")
    op.drop_constraint(
        "unique__app_templates__template_name_version", "app_templates", type_="unique"
    )

    # Create new composite unique constraint
    op.create_unique_constraint(
        "unique__app_templates__name_template_name_version",
        "app_templates",
        ["name", "template_name", "template_version"],
    )

    # Recreate the index on name (non-unique)
    op.create_index(
        op.f("ix_app_templates_name"), "app_templates", ["name"], unique=False
    )


def downgrade() -> None:
    # Drop the non-unique index on name
    op.drop_index(op.f("ix_app_templates_name"), table_name="app_templates")

    # Drop the composite unique constraint
    op.drop_constraint(
        "unique__app_templates__name_template_name_version",
        "app_templates",
        type_="unique",
    )

    # Restore the old unique constraints
    op.create_unique_constraint(
        "unique__app_templates__name", "app_templates", ["name"]
    )
    op.create_unique_constraint(
        "unique__app_templates__template_name_version",
        "app_templates",
        ["template_name", "template_version"],
    )

    # Restore the unique index on name
    op.create_index(
        op.f("ix_app_templates_name"), "app_templates", ["name"], unique=True
    )
