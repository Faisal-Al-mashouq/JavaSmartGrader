import asyncio
import logging

import redis.asyncio as redis
from backend.sandbox.schemas import (
    SandboxJobRequest,
)

logger = logging.getLogger(__name__)


class Sandbox:
    def __init__(self, redis_url: str, max_concurrency: int = 4):
        self.max_concurrency = max_concurrency
        self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)


async def start():
    client = Sandbox("redis://:mypass@localhost:6379", max_concurrency=4)
    logger.info("SandboxWorker started")
    await asyncio.gather(*(main_loop(client) for _ in range(client.max_concurrency)))


async def main_loop(client: Sandbox):
    while True:
        result = await client.redis_client.blpop("queue", timeout=0)
        logger.info(f"SandboxJob received: {result}")
        if result:
            _, job_data = result
            await process_job(job_data)


async def process_job(job_data: str):
    job = SandboxJobRequest.model_validate_json(job_data)

    try:
        logger.info(f"Processing Job: {job.job_id}")
        # Continue process
    except Exception as e:
        logger.error(f"SandboxJob error: {e}")


if __name__ == "__main__":
    asyncio.run(start())
