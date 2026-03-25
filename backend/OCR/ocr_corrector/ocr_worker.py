"""
OCR Worker — async job consumer from Redis queue.

Mirrors the sandbox_worker.py architecture:
- Async Redis with blmove (source → processing queue)
- N concurrent coroutines via asyncio.gather
- Job lifecycle: initialize → process → return result
- Graceful shutdown via KeyboardInterrupt

Queue design::

    {namespace}:OCRJobQueue                        → pending jobs
    {namespace}:OCRJobQueue:processing             → in-progress jobs
    {namespace}:OCRJobQueue:completed:{job_id}     → results
"""

import asyncio
import datetime
import logging

from redis.asyncio import Redis
from settings import settings

from .jobs import correct_job, flag_job, ocr_job, set_result
from .logs import setup_logging
from .schemas import (
    JobStatus,
    OCRJob,
    OCRJobRequest,
    OCRJobResult,
)

setup_logging()
logger = logging.getLogger(__name__)
OCR_QUEUE = f"{settings.queue_namespace}:OCRJobQueue"


class OCRWorkerClient:
    def __init__(
        self,
        redis_url: str = settings.redis_endpoint,
        max_concurrency: int = settings.max_concurrency,
    ):
        self.max_concurrency = max_concurrency
        self.redis_client = Redis.from_url(
            url=redis_url,
            decode_responses=True,
        )


async def start():
    try:
        logger.info("Starting OCR Worker...")
        client = OCRWorkerClient()
    except Exception as e:
        logger.exception("OCR Worker initialization error: %s", e)
        raise
    logger.info("OCR Worker started")
    try:
        await asyncio.gather(
            *(main_loop(client, pid) for pid in range(client.max_concurrency))
        )
    finally:
        await client.redis_client.aclose()
        logger.info("Redis connection closed.")


async def main_loop(
    client: OCRWorkerClient,
    process_id: int = 0,
):
    while True:
        try:
            logger.info(
                "Process #%d: Waiting for job in %s...",
                process_id,
                OCR_QUEUE,
            )
            result = await client.redis_client.blmove(
                OCR_QUEUE,
                f"{OCR_QUEUE}:processing",
                "RIGHT",
                "LEFT",
                timeout=0,
            )
        except asyncio.CancelledError:
            logger.debug(
                "Process #%d cancelled. Shutting down...",
                process_id,
            )
            return

        logger.info("OCR Job Received.")
        logger.debug("Details: %s", result)

        initialized_job = await initialize_job(result)
        if not initialized_job:
            logger.error("Failed to initialize job, skipping")
            await client.redis_client.lrem(f"{OCR_QUEUE}:processing", 1, result)
            continue

        processed_job = await process_job(initialized_job)
        if (
            processed_job.status != JobStatus.COMPLETED
            and processed_job.status != JobStatus.FAILED
        ):
            logger.error("Failed to process job, skipping")
            await client.redis_client.lrem(f"{OCR_QUEUE}:processing", 1, result)
            continue

        await return_result(client, processed_job)
        await client.redis_client.lrem(f"{OCR_QUEUE}:processing", 1, result)


async def initialize_job(
    job_request: str,
) -> OCRJob | None:
    logger.debug("Initializing OCRJob Request: %s", job_request)
    try:
        ocr_job_request = OCRJobRequest.model_validate_json(job_request)
        job = OCRJob(
            job_id=ocr_job_request.job_id,
            status=JobStatus.PENDING,
            created_at=datetime.datetime.now(datetime.UTC),
            request=ocr_job_request,
            result=None,
        )
        logger.debug(
            "OCRJob initialized successfully: %s",
            job.job_id,
        )
        return job
    except Exception as e:
        logger.error("Failed to initialize job: %s", e)
        return None


async def process_job(job: OCRJob) -> OCRJobResult:
    try:
        logger.info("Processing Job: %s", job.job_id)
        job.status = JobStatus.RUNNING

        # Step 1: Azure OCR extraction
        logger.debug("Job %s OCR extraction started", job.job_id)
        ocr_result = await ocr_job(job)
        if not ocr_result:
            logger.error(
                "OCR extraction failed for Job: %s",
                job.job_id,
            )
            return await set_result(job, JobStatus.FAILED)

        # Step 2: Gemini LLM correction
        logger.debug("Job %s LLM correction started", job.job_id)
        corrected_result = await correct_job(ocr_result)
        if not corrected_result:
            logger.error(
                "LLM correction failed for Job: %s",
                job.job_id,
            )
            return await set_result(ocr_result, JobStatus.FAILED)

        # Step 3: Flag detection (non-blocking)
        logger.debug("Job %s flag detection started", job.job_id)
        flagged_result = flag_job(corrected_result)

        logger.info("Job %s completed successfully", job.job_id)
        return await set_result(flagged_result, JobStatus.COMPLETED)

    except Exception as e:
        logger.exception("OCRJob error: %s", e)
        return await set_result(job, JobStatus.ERROR)


RESULT_TTL_SECONDS = 3600  # 1 hour


async def return_result(
    client: OCRWorkerClient,
    job: OCRJobResult,
):
    result_key = f"{OCR_QUEUE}:completed:{job.job_id}"
    await client.redis_client.lpush(result_key, job.model_dump_json())
    await client.redis_client.expire(result_key, RESULT_TTL_SECONDS)
    logger.debug(
        "OCR Job: %s result returned successfully",
        job.job_id,
    )
    return True


if __name__ == "__main__":
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        logger.info("OCR Worker shut down gracefully")
