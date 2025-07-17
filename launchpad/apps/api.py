from typing import Any

from fastapi import APIRouter
from fastapi_pagination import Page

from launchpad.apps.queries import select_public_apps_pool
from launchpad.apps.resources import AppPoolRead
from launchpad.db.dependencies import Db
from fastapi_pagination.ext.sqlalchemy import paginate


apps_router = APIRouter()


@apps_router.get("", response_model=Page[AppPoolRead])
async def view_get_apps_pool(db: Db) -> Any:
    query = select_public_apps_pool()
    return await paginate(db, query=query)
