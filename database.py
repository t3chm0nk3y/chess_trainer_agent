"""SQLAlchemy async setup, session factory."""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

import config

logger = logging.getLogger(__name__)

engine = create_async_engine(config.DATABASE_URL, echo=False)

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def init_db(retries: int = 5, delay: float = 2.0):
    """Create tables, retrying if DB is locked (e.g. pipeline running)."""
    for attempt in range(retries):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            return
        except Exception as e:
            if "database is locked" in str(e) and attempt < retries - 1:
                logger.warning(
                    "init_db: DB locked, retrying in %.0fs (%d/%d)",
                    delay, attempt + 1, retries,
                )
                await asyncio.sleep(delay)
            else:
                raise
