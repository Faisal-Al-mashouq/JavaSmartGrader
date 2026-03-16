import logging

from settings import settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)

ASYNC_DATABASE_URL = settings.async_database_url

logger.info("Initializing database engine")
engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
async_session = async_sessionmaker(bind=engine, expire_on_commit=False)


async def main():
    async with async_session() as session:
        result = await session.execute(text("SELECT version();"))
        version = result.fetchone()[0]
        logger.info("Database version: %s", version)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
