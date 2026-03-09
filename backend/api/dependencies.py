import logging

from db.session import async_session

logger = logging.getLogger(__name__)


async def get_db():
    logger.debug("Opening database session")
    async with async_session() as session:
        yield session
    logger.debug("Database session closed")
