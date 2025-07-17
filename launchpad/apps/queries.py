from sqlalchemy import select

from launchpad.apps.models import AppPool


def select_public_apps_pool():
    return (
        select(AppPool)
        .where(AppPool.is_internal.is_(False))
        .order_by(AppPool.name.asc())
    )
