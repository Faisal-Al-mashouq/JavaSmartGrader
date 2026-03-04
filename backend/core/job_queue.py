import asyncio
import logging
from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from schemas import Job, JobRequest, JobResult, JobStatus
from settings import settings

logger = logging.getLogger(__name__)


class JobQueue:
    def __init__(
        self,
        redis_url: str = settings.redis_endpoint,
        max_concurrency: int = settings.max_concurrency,
    ):
        self.redis_url: str = redis_url
        self.max_concurrency: int = max_concurrency
        self.redis_client = Redis.from_url(self.redis_url, decode_responses=True)


async def start():
    try:
        logger.info("Starting JobQueue...")
        client = JobQueue()
    except Exception as e:
        logger.error(f"Job Queue Initialization Failed: {e}")
        raise
    logger.info("Job Queue Started Successfully")
    await asyncio.gather(
        *(main_loop(client, pid) for pid in range(client.max_concurrency))
    )


async def main_loop(client: JobQueue, process_id: int = 0):
    while True:
        try:
            logger.info(f"Process #{process_id}: Waiting for Job in MainJobQueue...")
            result = await client.redis_client.brpoplpush(
                src="MainJobQueue", dst="MainJobQueue:processing", timeout=0
            )
        except asyncio.CancelledError:
            logger.debug(f"Process #{process_id} cancelled. Shutting down...")
            return
        logger.info("Job Received from MainJobQueue.")
        if result:
            logger.debug(f"Job Request: {result}")
            _, job_request = result

            initialized_job = await initialize_job(job_request)
            if not initialized_job:
                logger.error("Failed to initialize job, skipping...")
                continue

            processed_job = await process_job(initialized_job)
            if (
                processed_job.status != JobStatus.COMPLETE
                and processed_job.status != JobStatus.FAILED
            ):
                logger.error("Failed to process job, skipping...")
                continue

            await return_result(processed_job)


async def initialize_job(job_request: str) -> Job | None:
    logger.debug(f"Initializing Job Request: {job_request}")
    try:
        valid_job = JobRequest.model_validate_json(job_request)
        job = Job(
            id=valid_job.id,
            request=valid_job.request,
            status=JobStatus.PENDING,
            created_at=datetime.now(tz=UTC + timedelta(hours=3)),
            result=None,
        )
        logger.debug(f"Job initialized successfully: {job.id}")
        return job
    except Exception as e:
        logger.error(f"Failed to initialized job: {e}")
    return None


async def process_job(job: Job) -> JobResult:
    pass


async def return_result(job_result: JobResult):
    pass


if __name__ == "__main__":
    try:

        asyncio.run(start())
    except KeyboardInterrupt:
        logger.info("Job Queue shut down gracefully.")
