import json
from datetime import datetime

from schemas import (
    GraderPayload,
    GraderResult,
    Job,
    JobRequestPayload,
    JobResultPayload,
    JobStatus,
    JobType,
    SandboxResult,
)
from settings import settings

from ..config import JobQueue, logger

_queue_prefix = f"{settings.queue_namespace}:"
AI_GRADER_QUEUE = (
    settings.ready_grading_queue
    if settings.ready_grading_queue.startswith(_queue_prefix)
    else f"{_queue_prefix}{settings.ready_grading_queue}"
)


def _get_sandbox_result(job: Job) -> SandboxResult | None:
    return next(
        (
            p.job_result
            for p in job.job_result_payload
            if p.job_result and getattr(p.job_result, "type", None) == JobType.SANDBOX
        ),
        None,
    )


def _normalize_grader_payload(raw_result: dict) -> dict:
    if "rubric_result_json" in raw_result:
        return raw_result
    stripped = {
        key: value
        for key, value in raw_result.items()
        if key
        not in {
            "status",
            "error",
            "raw_output",
            "submission_id",
            "job_id",
        }
    }
    return {"rubric_result_json": stripped}


async def process_grader_job(client: JobQueue, job: Job) -> Job | None:
    try:
        logger.debug(f"Processing AI Grader Job: {job.job_id}")
        job.status = JobStatus.RUNNING

        sandbox_payload = _get_sandbox_result(job)
        if not sandbox_payload:
            logger.error(f"Sandbox result not found for Job: {job.job_id}")
            return None

        grader_payload = GraderPayload(
            type=JobType.GRADER,
            job_id=job.job_id,
            submission_id=job.initial_request.submission_id,
            transcribed_text=job.initial_request.java_code,
            sandbox_result=sandbox_payload.result,
            rubric_json=job.initial_request.rubric_json,
        )
        job.job_request_payload.append(
            JobRequestPayload(
                job_payload=grader_payload,
                created_at=datetime.now(),
            )
        )
        logger.debug(f"AI Grader Job: {job.job_id} pushed to {AI_GRADER_QUEUE}")
        await client.redis_client.lpush(
            AI_GRADER_QUEUE, grader_payload.model_dump_json()
        )
        _, result = await client.redis_client.brpop(
            f"{AI_GRADER_QUEUE}:completed:{job.job_id}", timeout=0
        )
        if not result:
            logger.error(f"AI Grader Job: {job.job_id} not found in {AI_GRADER_QUEUE}")
            return None

        raw_result = json.loads(result)
        status = raw_result.get("status")
        if status and status != JobStatus.COMPLETED:
            logger.error(
                "AI Grader Job %s returned status=%s",
                job.job_id,
                status,
            )
            return None

        normalized = _normalize_grader_payload(raw_result)
        grader_result = GraderResult.model_validate(
            {
                "type": JobType.GRADER,
                **normalized,
                "final_grade": raw_result.get("final_grade"),
                "student_feedback": raw_result.get("student_feedback"),
                "instructor_guidance": raw_result.get("instructor_guidance"),
            }
        )
        job.job_result_payload.append(
            JobResultPayload(
                job_result=grader_result,
                finished_at=datetime.now(),
            )
        )
        job.status = JobStatus.PENDING
        logger.debug(f"AI Grader Job: {job.job_id} completed")
        return job
    except Exception as e:
        logger.error(f"Failed to process AI Grader Job: {job.job_id} - {e}")
        return None
