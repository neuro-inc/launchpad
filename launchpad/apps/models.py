from typing import Any
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSON

from launchpad.db.base import Base


UNIQUE__INSTALLED_APPS__LAUNCHPAD_APP_NAME__USER_ID = UniqueConstraint(
    "app_id",
    name="unique__installed_apps__launchpad_app_name__user_id",
    postgresql_nulls_not_distinct=True,
)


class InstalledApp(Base):
    __tablename__ = "installed_apps"

    __table_args__ = (UNIQUE__INSTALLED_APPS__LAUNCHPAD_APP_NAME__USER_ID,)

    app_id: Mapped[UUID]
    """ID returned by an apps api
    """
    app_name: Mapped[str]
    """Name returned by an apps api
    """
    launchpad_app_name: Mapped[str] = mapped_column(index=True)
    """Internal launchpad app name
    """
    is_internal: Mapped[bool]
    """Internal apps are not visible for end-users, but required by other apps
    """
    is_shared: Mapped[bool]
    """This app can be used in a shared mode by all launchpad users without having an app instance per user.
    """
    user_id: Mapped[str | None]
    url: Mapped[str | None]
    template_name: Mapped[str]
    """Template name used for installation
    """
    template_version: Mapped[str]
    """Template version used for installation
    """
    verbose_name: Mapped[str]
    """User-friendly display name
    """
    description_short: Mapped[str]
    """Short description of the app
    """
    description_long: Mapped[str]
    """Long description of the app
    """
    logo: Mapped[str]
    """URL to the app's logo
    """
    documentation_urls: Mapped[list[dict[str, str]]] = mapped_column(JSON)
    """List of documentation URLs
    """
    external_urls: Mapped[list[dict[str, str]]] = mapped_column(JSON)
    """List of external URLs
    """
    tags: Mapped[list[str]] = mapped_column(JSON)
    """List of tags for categorization
    """
