from typing import TYPE_CHECKING

import aiohttp
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from launchpad.auth.oauth import Oauth
from launchpad.config import Config
from launchpad.ext.apps_api import AppsApiClient


if TYPE_CHECKING:
    from launchpad.apps.service import AppService


class Launchpad(FastAPI):
    config: Config
    db_engine: AsyncEngine
    db: async_sessionmaker[AsyncSession]
    http: aiohttp.ClientSession
    apps_api_client: AppsApiClient
    app_service: "AppService"
    oauth: "Oauth"
