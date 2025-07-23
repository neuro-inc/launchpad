from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from launchpad.db.base import Base


UNIQUE__APP_ID = UniqueConstraint("app_id", name="unique__installed_apps__app_id")


class InstalledApp(Base):
    __tablename__ = "installed_apps"

    __table_args__ = (UNIQUE__APP_ID,)

    app_id: Mapped[UUID]
    """ID returned by an apps api
    """
    app_name: Mapped[str]
    """Name returned by an apps api
    """
    launchpad_name: Mapped[str] = mapped_column(index=True)
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
