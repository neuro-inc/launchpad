from uuid import UUID

from sqlalchemy import true, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from launchpad.db.base import Base


class AppPool(Base):
    __tablename__ = "apps_pool"

    name: Mapped[str]
    description: Mapped[str]
    is_internal: Mapped[bool] = mapped_column(server_default=true())
    is_shared: Mapped[bool] = mapped_column(server_default=true())


class AppInstance(Base):
    __tablename__ = "apps_instances"

    app_id: Mapped[UUID] = mapped_column(ForeignKey("apps_pool.id"))
    state: Mapped[int]
    url: Mapped[str]
