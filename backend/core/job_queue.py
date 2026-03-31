import asyncio
import logging
from datetime import datetime
from uuid import uuid4

from schemas import Job, JobRequest, JobStatus
from settings import settings

from .config import JobQueue
from .process import (
    # process_final_result_job,
    process_grader_job,
    process_ocr_job,
    process_sandbox_job,
)

logger = logging.getLogger(__name__)
MAIN_QUEUE = f"{settings.queue_namespace}:MainJobQueue"


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
            logger.info(f"Process #{process_id}: Waiting for Job in {MAIN_QUEUE}...")
            result = await client.redis_client.brpoplpush(
                src=MAIN_QUEUE, dst=f"{MAIN_QUEUE}:processing", timeout=0
            )
        except asyncio.CancelledError:
            logger.debug(f"Process #{process_id} cancelled. Shutting down...")
            return
        logger.info(f"Job Received from {MAIN_QUEUE}.")
        if result:
            logger.debug(f"Job Request: {result}")
            job_request = result

            initialized_job = await initialize_job(job_request)
            if not initialized_job:
                logger.error("Failed to initialize job, skipping...")
                continue

            processed_job = await process_job(client, initialized_job)
            if processed_job.status in [JobStatus.FAILED, JobStatus.ERROR]:
                logger.error("Failed to process job, skipping...")
                await client.redis_client.lrem(f"{MAIN_QUEUE}:processing", 1, result)
                continue
            logger.debug(f"Returning Job Result: {processed_job.model_dump_json()}")

            returned_result = await return_result(client, processed_job)
            if not returned_result:
                logger.error("Failed to return job result, skipping...")
                await client.redis_client.lrem(f"{MAIN_QUEUE}:processing", 1, result)
                continue

            logger.info(f"Job {processed_job.job_id} Completed Successfully")
        await client.redis_client.lrem(f"{MAIN_QUEUE}:processing", 1, result)


async def initialize_job(job_request: str) -> Job | None:
    logger.debug(f"Initializing Job Request: {job_request}")
    try:
        valid_job = JobRequest.model_validate_json(job_request)
        job = Job(
            job_id=uuid4(),
            status=JobStatus.PENDING,
            initial_request=valid_job,
            created_at=datetime.now(),
            finished_at=None,
        )
        logger.debug(f"Job initialized successfully: {job.job_id}")
        return job
    except Exception as e:
        logger.error(f"Failed to initialized job: {e}")
    return None


async def process_job(client: JobQueue, job: Job) -> Job:
    try:
        logger.debug(f"Processing Job: {job.job_id}")
        job.status = JobStatus.STARTED

        logger.debug(f"Job {job.job_id} OCR Started")
        ocr_result = await process_ocr_job(client, job)
        if not ocr_result:
            logger.error(f"Failed to process OCR for Job: {job.job_id}")
            return await set_result(job, JobStatus.FAILED)
        logger.debug(f"Job {job.job_id} OCR Completed")

        logger.debug(f"Job {job.job_id} Sandbox Started")
        sandbox_result = await process_sandbox_job(client, job)
        if not sandbox_result:
            logger.error(f"Failed to process Sandbox for Job: {job.job_id}")
            return await set_result(job, JobStatus.FAILED)
        logger.debug(f"Job {job.job_id} Sandbox Completed")

        logger.debug(f"Job {job.job_id} Grader Started")
        grader_result = await process_grader_job(client, job)
        if not grader_result:
            logger.error(f"Failed to process Grader for Job: {job.job_id}")
            return await set_result(job, JobStatus.FAILED)
        logger.debug(f"Job {job.job_id} Grader Completed")

        # logger.debug(f"Job {job.job_id} Final Result Started")
        # final_result = await process_final_result_job(client, job)
        # if not final_result:
        #     logger.error(f"Failed to process Final Result for Job: {job.job_id}")
        #     return await set_result(job, JobStatus.FAILED)
        # logger.debug(f"Job {job.job_id} Final Result Completed")

        logger.info(f"Job {job.job_id} Completed Successfully")
        logger.debug(f"Job {job.job_id} Result: {job.job_result_payload}")
        return await set_result(job, JobStatus.COMPLETED)

    except Exception as e:
        logger.error(f"Failed to process job: {e}")
        return await set_result(job, JobStatus.ERROR)


async def set_result(job: Job, status: JobStatus):
    job.status = status
    job.finished_at = datetime.now()
    logger.debug(f"Job {job.job_id} Result: {job.model_dump_json()}")
    return job


async def return_result(client: JobQueue, job: Job) -> bool:
    logger.debug(f"Returning Job Result: {job.model_dump_json()}")
    try:
        await client.redis_client.lpush(
            f"{MAIN_QUEUE}:completed", job.model_dump_json()
        )
        logger.debug(f"Job Result returned successfully: {job.finished_at}")
        return True
    except Exception as e:
        logger.error(f"Failed to return job result: {e}")
        return False
