import os

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

load_dotenv()
DATABASE_URL = os.getenv("ASYNC_DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(bind=engine, expire_on_commit=False)


async def main():
    async with async_session() as session:
        result = await session.execute(text("SELECT version();"))
        version = result.fetchone()[0]
        print(f"Database version: {version}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
