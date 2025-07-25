import aiohttp
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, AsyncSession

from launchpad.config import Config
from launchpad.ext.apps_api import AppsApiClient


class Launchpad(FastAPI):
    config: Config
    db_engine: AsyncEngine
    db: async_sessionmaker[AsyncSession]
    http: aiohttp.ClientSession
    apps_api_client: AppsApiClient
