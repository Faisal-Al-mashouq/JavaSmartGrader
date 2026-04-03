import asyncio
import datetime
import logging

from redis.asyncio import Redis
from settings import settings

from .helpers import _cleanup_workspace, docker_build_images
from .jobs import (
    compile_job,
    execute_job,
    run_test_cases,
    set_result,
)
from .logs import setup_logging
from .schemas import (
    JobStatus,
    SandboxJob,
    SandboxJobRequest,
    SandboxJobResult,
)

setup_logging()
logger = logging.getLogger(__name__)
SANDBOX_QUEUE = f"{settings.queue_namespace}:{settings.sandbox_queue}"


class Sandbox:
    def __init__(
        self,
        redis_url: str = settings.redis_endpoint,
        sandbox_max_concurrency: int = settings.sandbox_max_concurrency,
    ):
        self.sandbox_max_concurrency = sandbox_max_concurrency
        self.redis_client = Redis.from_url(url=redis_url, decode_responses=True)


async def start():
    try:
        logger.info("Starting Sandbox Worker...")
        await docker_build_images()
        client = Sandbox()
    except Exception as e:
        logger.exception("Sandbox Worker Initialization error: %s", e)
        raise
    logger.info("Sandbox Worker started")
    await asyncio.gather(
        *(main_loop(client, pid) for pid in range(client.sandbox_max_concurrency))
    )


async def main_loop(client: Sandbox, process_id: int = 0):
    while True:
        try:
            logger.info(f"Process #{process_id}: Waiting for job in {SANDBOX_QUEUE}...")
            result = await client.redis_client.brpoplpush(
                src=SANDBOX_QUEUE, dst=f"{SANDBOX_QUEUE}:processing", timeout=0
            )
        except asyncio.CancelledError:
            logger.debug(f"Process #{process_id} cancelled. Shutting down...")
            return
        logger.info("Sandbox Job Received.")
        if result:
            logger.debug(f"Details: {result}")
            initialized_job = await initialize_job(result)
            if not initialized_job:
                logger.error("Failed to initialize job, skipping")
                continue

            processed_job = await process_job(initialized_job)
            if (
                processed_job.status != JobStatus.COMPLETED
                and processed_job.status != JobStatus.FAILED
            ):
                logger.error("Failed to process job, skipping")
                continue

            await return_result(client, processed_job)
            await client.redis_client.lrem(f"{SANDBOX_QUEUE}:processing", 1, result)
        else:
            logger.error(f"No job found in {SANDBOX_QUEUE}")
            await client.redis_client.lrem(f"{SANDBOX_QUEUE}:processing", 1, result)
            continue


async def initialize_job(job_request: str) -> SandboxJob | None:
    logger.debug(f"Initializing SandboxJob Request: {job_request}")
    try:
        sandbox_job_request = SandboxJobRequest.model_validate_json(job_request)
        job = SandboxJob(
            job_id=sandbox_job_request.job_id,
            status=JobStatus.PENDING,
            created_at=datetime.datetime.now(),
            request=sandbox_job_request,
            result=None,
        )
        logger.debug(f"SandboxJob initialized successfully: {job.job_id}")
        return job
    except Exception as e:
        logger.error(f"Failed to initialize job: {e}")
        return None


async def process_job(job: SandboxJob) -> SandboxJobResult:
    try:
        logger.info(f"Processing Job: {job.job_id}")
        job.status = JobStatus.RUNNING

        logger.debug(f"Job {job.job_id} compilation started")
        compiled_job = await compile_job(job)
        if not compiled_job:
            logger.error(f"Compilation failed for Job: {job.job_id}")
            return await set_result(job, JobStatus.FAILED)

        logger.debug(f"Job {job.job_id} execution started")
        executed_job = await execute_job(compiled_job)
        if not executed_job:
            logger.error(f"Execution failed for Job: {job.job_id}")
            return await set_result(compiled_job, JobStatus.FAILED)

        logger.debug(f"Job {job.job_id} evaluating test cases")
        tested_job = run_test_cases(executed_job)

        logger.info(f"Job {job.job_id} completed successfully")
        return await set_result(tested_job, JobStatus.COMPLETED)
    except Exception as e:
        logger.exception("SandboxJob error: %s", e)
        return await set_result(job, JobStatus.ERROR)
    finally:
        _cleanup_workspace(job.job_id)


async def return_result(client: Sandbox, job: SandboxJobResult):
    await client.redis_client.lpush(
        f"{SANDBOX_QUEUE}:completed:{job.job_id}", job.model_dump_json()
    )
    logger.debug(f"Sandbox Job: {job.job_id} result returned successfully")
    return True


if __name__ == "__main__":
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        logger.info("Sandbox Worker shut down gracefully")
