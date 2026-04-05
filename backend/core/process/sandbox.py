import json
from datetime import datetime

from db.crud.grading import create_compile_result
from db.crud.submissions import get_submission_by_id
from db.session import async_session
from schemas import (
    Job,
    JobRequestPayload,
    JobResultPayload,
    JobStatus,
    JobType,
    SandboxPayload,
    SandboxResult,
)
from settings import settings

from ..config import JobQueue, logger
from .ocr import resolve_java_code_for_job

SANDBOX_QUEUE = f"{settings.queue_namespace}:{settings.sandbox_queue}"


async def process_sandbox_job(client: JobQueue, job: Job) -> Job | None:
    try:
        logger.debug(f"Processing Sandbox Job: {job.job_id}")
        job.status = JobStatus.RUNNING
        corrected_text = await resolve_java_code_for_job(job)
        sandbox_payload = SandboxPayload(
            type=JobType.SANDBOX,
            job_id=job.job_id,
            java_code=corrected_text,
            test_cases=job.initial_request.test_cases,
        )
        job.job_request_payload.append(
            JobRequestPayload(
                job_payload=sandbox_payload,
                created_at=datetime.now(),
            )
        )
        logger.debug(f"Sandbox Job: {job.job_id} pushed to {SANDBOX_QUEUE}")
        await client.redis_client.lpush(
            SANDBOX_QUEUE, sandbox_payload.model_dump_json()
        )
        _, result = await client.redis_client.brpop(
            f"{SANDBOX_QUEUE}:completed:{job.job_id}", timeout=0
        )
        if not result:
            logger.error(f"Sandbox Job: {job.job_id} not found in {SANDBOX_QUEUE}")
            return None
        raw_result = json.loads(result)
        sandbox_result = SandboxResult.model_validate(
            {"type": JobType.SANDBOX, "result": raw_result}
        )
        job.job_result_payload.append(
            JobResultPayload(
                job_result=sandbox_result,
                finished_at=datetime.now(),
            )
        )
        job.status = JobStatus.PENDING
        logger.debug(f"Sandbox Job: {job.job_id} completed")
        if not await save_to_db(job):
            logger.error(f"Failed to save Sandbox Job: {job.job_id} to database")
            return None
        return job
    except Exception as e:
        logger.error(f"Failed to process Sandbox Job: {job.job_id} - {e}")
        return None


async def save_to_db(job: Job) -> bool:

    try:
        async with async_session() as session:
            logger.debug(f"Saving Sandbox Job: {job.job_id} to database")
            sandbox_payload = next(
                (
                    p.job_result
                    for p in job.job_result_payload
                    if p.job_result
                    and getattr(p.job_result, "type", None) == JobType.SANDBOX
                ),
                None,
            )
            if not sandbox_payload:
                logger.error(f"Sandbox Payload not found for Sandbox Job: {job.job_id}")
                return False
            sandbox_job_result = sandbox_payload.result
            sandbox_result = sandbox_job_result.result
            if not sandbox_result or not sandbox_result.compilation_result:
                logger.error(
                    f"Sandbox Result or Compilation Result not found"
                    f" for Sandbox Job: {job.job_id}"
                )
                return False

            submission = await get_submission_by_id(
                session, job.initial_request.submission_id
            )
            if not submission:
                logger.error(
                    f"Submission {job.initial_request.submission_id} not found - "
                    "cannot save compile result. Ensure the submission exists "
                )
                return False

            execution_result = sandbox_result.execution_result
            compile_result = await create_compile_result(
                session=session,
                submission_id=job.initial_request.submission_id,
                compiled_ok=sandbox_result.compilation_result.success,
                compile_errors=json.dumps(sandbox_result.compilation_result.errors),
                runtime_errors=json.dumps(execution_result.errors),
                runtime_outputs=(
                    json.dumps([o.model_dump() for o in execution_result.outputs])
                    if execution_result and execution_result.outputs
                    else None
                ),
            )
            if compile_result:
                logger.debug(f"Compile Result: {compile_result.id} saved to database")
                return True
            logger.error(f"Failed to save Compile Result for Sandbox Job: {job.job_id}")
            return False
    except Exception as e:
        logger.error(f"Failed to save Sandbox Job: {job.job_id} to database - {e}")
        return False
