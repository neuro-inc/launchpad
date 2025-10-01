from typing import Any
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSON

from launchpad.db.base import Base


class AppTemplate(Base):
    """
    Represents an app template that can be installed.
    Acts as the source of truth for available apps in the pool.
    """

    __tablename__ = "app_templates"

    __table_args__ = (
        UniqueConstraint(
            "name",
            name="unique__app_templates__name",
        ),
    )

    name: Mapped[str] = mapped_column(index=True, unique=True)
    """Unique template identifier/name"""

    template_name: Mapped[str]
    """Apps API template name"""

    template_version: Mapped[str]
    """Apps API template version"""

    verbose_name: Mapped[str]
    """User-friendly display name"""

    description_short: Mapped[str]
    """Short description of the template"""

    description_long: Mapped[str]
    """Long description of the template"""

    logo: Mapped[str]
    """URL to the template's logo"""

    documentation_urls: Mapped[list[dict[str, str]]] = mapped_column(JSON)
    """List of documentation URLs"""

    external_urls: Mapped[list[dict[str, str]]] = mapped_column(JSON)
    """List of external URLs"""

    tags: Mapped[list[str]] = mapped_column(JSON)
    """List of tags for categorization"""

    is_internal: Mapped[bool]
    """Whether this template is internal (not visible to end users)"""

    is_shared: Mapped[bool]
    """Whether apps from this template can be shared by multiple users"""

    handler_class: Mapped[str | None]
    """Optional handler class name (e.g., 'OpenWebUIApp'). If None, uses GenericApp"""

    default_inputs: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    """Default inputs to merge with user-provided inputs"""
