import logging

logger = logging.getLogger(__name__)


async def get_db():
    from db.session import async_session

    logger.debug("Opening database session")
    async with async_session() as session:
        yield session
    logger.debug("Database session closed")
