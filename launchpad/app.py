import aiohttp
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from launchpad.config import Config


class App(FastAPI):
    config: Config
    db_engine: AsyncEngine
    db: async_sessionmaker
    http: aiohttp.ClientSession
