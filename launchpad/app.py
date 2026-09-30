from typing import TYPE_CHECKING

import aiohttp
from apolo_sdk import Client as ApoloClient
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from launchpad.auth.oauth import Oauth
from launchpad.config import Config
from launchpad.ext.app_configurator import AppConfigurator
from launchpad.ext.apps_api import AppsApiClient


if TYPE_CHECKING:
    from launchpad.apps.service import AppService
    from launchpad.auth.static_hostname import StaticHostnameAuthService


class Launchpad(FastAPI):
    config: Config
    db_engine: AsyncEngine
    db: async_sessionmaker[AsyncSession]
    http: aiohttp.ClientSession
    apolo_client: ApoloClient
    apps_api_client: AppsApiClient
    app_configurator: AppConfigurator
    app_service: "AppService"
    oauth: "Oauth"
    static_hostname_auth: "StaticHostnameAuthService"
