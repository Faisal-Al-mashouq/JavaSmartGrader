import asyncio
import datetime
import logging
import os
import sys

import redis.asyncio as redis
from dotenv import load_dotenv

from .helpers import SANDBOX_TMP_DIR, _cleanup_workspace, docker_build_images
from .jobs import (
    compile_job,
    execute_job,
    run_test_cases,
    set_result,
)
from .schemas import (
    JobStatus,
    SandboxJob,
    SandboxJobRequest,
    SandboxJobResult,
)

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class Sandbox:
    def __init__(self, redis_url: str, max_concurrency: int = 4):
        self.max_concurrency = max_concurrency
        self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)


async def start():
    try:
        logger.info("Starting Sandbox Worker...")
        await docker_build_images()
        client = Sandbox(os.getenv("REDIS_ENDPOINT"), max_concurrency=4)
    except Exception as e:
        logger.error(f"Sandbox Worker Initialization error: {e}")
        raise
    logger.info("Sandbox Worker started")
    await asyncio.gather(
        *(main_loop(client, pid) for pid in range(client.max_concurrency))
    )


async def main_loop(client: Sandbox, process_id: int = 0):
    while True:
        try:
            logger.info(f"Process #{process_id}: Waiting for job in SandboxJobQueue...")
            result = await client.redis_client.blpop("SandboxJobQueue", timeout=0)
        except asyncio.CancelledError:
            return
        logger.info(f"SandboxJob received: {result}")
        if result:
            _, job_request = result

            initialized_job = await initialize_job(job_request)
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

            await save_result(processed_job)


async def initialize_job(job_request: str) -> SandboxJob | None:
    logger.info(f"Initializing Job request: {job_request}")
    try:
        sandbox_job_request = SandboxJobRequest.model_validate_json(job_request)
        job = SandboxJob(
            job_id=sandbox_job_request.job_id,
            status=JobStatus.PENDING,
            created_at=datetime.datetime.now(),
            request=sandbox_job_request,
            result=None,
        )
        logger.info(f"Job initialized successfully: {job.job_id}")
        return job
    except Exception as e:
        logger.error(f"Failed to initialize job: {e}")
        return None


async def process_job(job: SandboxJob) -> SandboxJobResult:
    try:
        logger.info(f"Processing Job: {job.job_id}")
        job.status = JobStatus.RUNNING

        logger.info(f"Job {job.job_id} compilation started")
        compiled_job = await compile_job(job)
        if not compiled_job:
            logger.error(f"Compilation failed for Job: {job.job_id}")
            return await set_result(job, JobStatus.FAILED)

        logger.info(f"Job {job.job_id} execution started")
        executed_job = await execute_job(compiled_job)
        if not executed_job:
            logger.error(f"Execution failed for Job: {job.job_id}")
            return await set_result(compiled_job, JobStatus.FAILED)

        logger.info(f"Job {job.job_id} evaluating test cases")
        tested_job = run_test_cases(executed_job)

        logger.info(f"Job {job.job_id} completed successfully")
        return await set_result(tested_job, JobStatus.COMPLETED)
    except Exception as e:
        logger.error(f"SandboxJob error: {e}")
        return await set_result(job, JobStatus.ERROR)
    finally:
        _cleanup_workspace(job.job_id)


async def save_result(job: SandboxJobResult):
    """
    In production, this would save to a database or object storage.
    For testing, we save to a local file.
    """
    results_dir = SANDBOX_TMP_DIR / "test_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    result_file = results_dir / f"{job.job_id}.txt"
    result_file.write_text(job.model_dump_json(indent=2))
    logger.info(f"Job result saved to {result_file}")


if __name__ == "__main__":
    try:
        # This should be used only for testing the worker locally
        # In production we will push jobs to the queue from the API server
        asyncio.run(start())
    except KeyboardInterrupt:
        logger.info("Sandbox Worker shut down gracefully")
