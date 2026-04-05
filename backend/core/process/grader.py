import json
from datetime import datetime
from typing import Any

from db.crud.submissions import get_submission_by_id
from db.models import AIFeedback, SubmissionState
from db.session import async_session
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
from sqlalchemy import select

from ..config import JobQueue, logger
from .ocr import resolve_java_code_for_job

_queue_prefix = f"{settings.queue_namespace}:"
AI_GRADER_QUEUE = (
    settings.ai_grading_queue
    if settings.ai_grading_queue.startswith(_queue_prefix)
    else f"{_queue_prefix}{settings.ai_grading_queue}"
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


def _normalize_grader_payload(raw_result: dict[str, Any]) -> dict[str, Any]:
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


def _extract_summary(rubric_result_json: dict[str, Any]) -> str | None:
    feedback = rubric_result_json.get("feedback")
    if not isinstance(feedback, dict):
        return None
    summary = feedback.get("summary")
    if isinstance(summary, str):
        stripped = summary.strip()
        return stripped or None
    return None


def _coerce_final_grade(
    value: Any,
    *,
    rubric_result_json: dict[str, Any],
) -> float | None:
    if value is not None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    total_score = rubric_result_json.get("total_score")
    if total_score is None:
        return None
    try:
        return float(total_score)
    except (TypeError, ValueError):
        return None


async def _save_success_to_db(
    *,
    submission_id: int,
    raw_result: dict[str, Any],
    grader_result: GraderResult,
) -> bool:
    rubric_result_json = grader_result.rubric_result_json
    final_grade = _coerce_final_grade(
        raw_result.get("final_grade"),
        rubric_result_json=rubric_result_json,
    )

    student_feedback = raw_result.get("student_feedback")
    if not isinstance(student_feedback, str) or not student_feedback.strip():
        student_feedback = _extract_summary(rubric_result_json)
    else:
        student_feedback = student_feedback.strip()

    instructor_guidance = raw_result.get("instructor_guidance")
    if not isinstance(instructor_guidance, str) or not instructor_guidance.strip():
        instructor_guidance = json.dumps(
            rubric_result_json,
            ensure_ascii=True,
            indent=2,
        )
    else:
        instructor_guidance = instructor_guidance.strip()

    try:
        async with async_session() as session:
            submission = await get_submission_by_id(session, submission_id)
            if not submission:
                logger.error(
                    "Submission %s not found - cannot save AI feedback.",
                    submission_id,
                )
                return False

            existing_result = await session.execute(
                select(AIFeedback).where(AIFeedback.submission_id == submission_id)
            )
            existing_feedback = existing_result.scalar_one_or_none()

            if existing_feedback is None:
                session.add(
                    AIFeedback(
                        submission_id=submission_id,
                        suggested_grade=final_grade,
                        instructor_guidance=instructor_guidance,
                        student_feedback=student_feedback,
                    )
                )
            else:
                existing_feedback.suggested_grade = final_grade
                existing_feedback.instructor_guidance = instructor_guidance
                existing_feedback.student_feedback = student_feedback

            submission.state = SubmissionState.graded
            await session.commit()
            return True
    except Exception as exc:
        logger.error(
            "Failed to persist successful AI grading for submission %s: %s",
            submission_id,
            exc,
        )
        return False


async def _save_failure_to_db(
    *,
    submission_id: int,
    reason: str,
    raw_output: str | None = None,
) -> bool:
    failure_payload = {
        "submission_id": submission_id,
        "status": "ai_grading_failed",
        "reason": reason,
    }
    if raw_output:
        failure_payload["raw_model_output"] = raw_output

    failure_text = json.dumps(
        failure_payload,
        ensure_ascii=True,
        indent=2,
    )

    try:
        async with async_session() as session:
            submission = await get_submission_by_id(session, submission_id)
            if not submission:
                logger.error(
                    "Submission %s not found - cannot persist AI grading failure.",
                    submission_id,
                )
                return False

            existing_result = await session.execute(
                select(AIFeedback).where(AIFeedback.submission_id == submission_id)
            )
            existing_feedback = existing_result.scalar_one_or_none()

            if existing_feedback is None:
                session.add(
                    AIFeedback(
                        submission_id=submission_id,
                        suggested_grade=None,
                        instructor_guidance=failure_text,
                        student_feedback=None,
                    )
                )
            else:
                existing_feedback.suggested_grade = None
                existing_feedback.instructor_guidance = failure_text
                existing_feedback.student_feedback = None

            submission.state = SubmissionState.failed
            await session.commit()
            return True
    except Exception as exc:
        logger.error(
            "Failed to persist AI grading failure for submission %s: %s",
            submission_id,
            exc,
        )
        return False


async def process_grader_job(client: JobQueue, job: Job) -> Job | None:
    submission_id = job.initial_request.submission_id
    try:
        logger.debug("Processing AI Grader Job: %s", job.job_id)
        job.status = JobStatus.RUNNING

        sandbox_payload = _get_sandbox_result(job)
        if not sandbox_payload:
            logger.error("Sandbox result not found for Job: %s", job.job_id)
            await _save_failure_to_db(
                submission_id=submission_id,
                reason="Sandbox result missing before AI grading.",
            )
            return None

        transcribed = await resolve_java_code_for_job(job)
        grader_payload = GraderPayload(
            type=JobType.GRADER,
            job_id=job.job_id,
            submission_id=submission_id,
            transcribed_text=transcribed,
            sandbox_result=sandbox_payload.result,
            rubric_json=job.initial_request.rubric_json,
        )
        job.job_request_payload.append(
            JobRequestPayload(
                job_payload=grader_payload,
                created_at=datetime.now(),
            )
        )

        logger.debug("AI Grader Job: %s pushed to %s", job.job_id, AI_GRADER_QUEUE)
        await client.redis_client.lpush(
            AI_GRADER_QUEUE,
            grader_payload.model_dump_json(),
        )

        _, result = await client.redis_client.brpop(
            f"{AI_GRADER_QUEUE}:completed:{job.job_id}",
            timeout=0,
        )
        if not result:
            logger.error(
                "AI Grader Job: %s not found in %s",
                job.job_id,
                AI_GRADER_QUEUE,
            )
            await _save_failure_to_db(
                submission_id=submission_id,
                reason="AI grader completion payload not received.",
            )
            return None

        raw_result = json.loads(result)
        status = raw_result.get("status")
        if status and status != JobStatus.COMPLETED:
            error_reason = str(
                raw_result.get("error")
                or f"AI grader returned non-completed status: {status}"
            )
            logger.error("AI Grader Job %s returned status=%s", job.job_id, status)
            await _save_failure_to_db(
                submission_id=submission_id,
                reason=error_reason,
                raw_output=raw_result.get("raw_output"),
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

        if not await _save_success_to_db(
            submission_id=submission_id,
            raw_result=raw_result,
            grader_result=grader_result,
        ):
            await _save_failure_to_db(
                submission_id=submission_id,
                reason="Failed to persist successful AI grading output to DB.",
                raw_output=raw_result.get("raw_output"),
            )
            return None

        job.status = JobStatus.PENDING
        logger.debug("AI Grader Job: %s completed", job.job_id)
        return job
    except Exception as exc:
        logger.error("Failed to process AI Grader Job: %s - %s", job.job_id, exc)
        await _save_failure_to_db(
            submission_id=submission_id,
            reason=str(exc),
        )
        return None
