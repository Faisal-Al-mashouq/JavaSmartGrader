import asyncio

import redis.asyncio as redis


class Sandbox:
    def __init__(self, redis_url: str, max_concurrency: int = 4):
        self.max_concurrency = max_concurrency
        self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)


# async def start():
#     client = Sandbox("redis://:mypass@localhost:6379", max_concurrency=4)


async def _main_loop():
    shutdown_event = asyncio.Event()  # Define the shutdown_event
    while not shutdown_event.is_set():
        # Check for new jobs in the queue
        job = await get_next_job()
        if job:
            # Process the job
            await process_job(job)
        else:
            # Sleep for a short period before checking again
            await asyncio.sleep(1)


async def get_next_job():
    pass


async def process_job(job):
    pass
