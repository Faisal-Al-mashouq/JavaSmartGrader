import json
from typing import Any

from db.crud.submissions import get_submission_by_id
from db.models import AIFeedback, SubmissionState
from db.session import async_session
from datetime import datetime

from schemas import FinalResult, GraderResult, Job, JobResultPayload, JobStatus, JobType
from sqlalchemy import select

from ..config import JobQueue, logger


def _get_grader_result(job: Job) -> GraderResult | None:
    return next(
        (
            payload.job_result
            for payload in job.job_result_payload
            if payload.job_result and getattr(payload.job_result, "type", None) == JobType.GRADER
        ),
        None,
    )


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


def _format_instructor_guidance(rubric_result_json: dict[str, Any]) -> str:
    feedback = rubric_result_json.get("feedback")
    rubric_breakdown = rubric_result_json.get("rubric_breakdown")
    error_classification = rubric_result_json.get("error_classification")
    confidence = rubric_result_json.get("confidence")
    total_score = rubric_result_json.get("total_score")
    max_score = rubric_result_json.get("max_score")

    lines: list[str] = []

    summary = _extract_summary(rubric_result_json)
    if summary:
        lines.append(f"Summary: {summary}")

    if total_score is not None and max_score is not None:
        lines.append(f"Score: {total_score}/{max_score}")

    if isinstance(confidence, (int, float)):
        lines.append(f"Confidence: {confidence}")

    if isinstance(rubric_breakdown, list) and rubric_breakdown:
        lines.append("Rubric breakdown:")
        for item in rubric_breakdown:
            if not isinstance(item, dict):
                continue
            criterion = item.get("criterion_id_or_name", "Unknown criterion")
            earned = item.get("earned_points", "?")
            maximum = item.get("max_points", "?")
            rationale = str(item.get("rationale", "")).strip()
            evidence = str(item.get("evidence_from_code_or_logs", "")).strip()
            lines.append(f"- {criterion}: {earned}/{maximum}")
            if rationale:
                lines.append(f"  rationale: {rationale}")
            if evidence:
                lines.append(f"  evidence: {evidence}")

    if isinstance(feedback, dict):
        issues = feedback.get("issues")
        suggestions = feedback.get("suggestions")
        next_steps = feedback.get("next_steps")

        if isinstance(issues, list) and issues:
            lines.append("Key issues:")
            for issue in issues:
                if not isinstance(issue, dict):
                    continue
                description = str(issue.get("description", "")).strip()
                severity = str(issue.get("severity", "")).strip()
                location = str(issue.get("location", "")).strip()
                issue_line = description or "Unspecified issue"
                if severity:
                    issue_line += f" [{severity}]"
                if location:
                    issue_line += f" @ {location}"
                lines.append(f"- {issue_line}")

        if isinstance(suggestions, list) and suggestions:
            lines.append("Suggestions:")
            for suggestion in suggestions:
                text = str(suggestion).strip()
                if text:
                    lines.append(f"- {text}")

        if isinstance(next_steps, list) and next_steps:
            lines.append("Next steps:")
            for step in next_steps:
                text = str(step).strip()
                if text:
                    lines.append(f"- {text}")

    if isinstance(error_classification, dict):
        categories: list[str] = []
        for key in (
            "handwriting_ocr_suspected",
            "syntax_or_compile",
            "runtime",
            "logic",
        ):
            if error_classification.get(key):
                categories.append(key.replace("_", " "))

        notes = str(error_classification.get("notes", "")).strip()
        if categories:
            lines.append("Error classification: " + ", ".join(categories))
        if notes:
            lines.append(f"Classification notes: {notes}")

    formatted = "\n".join(lines).strip()
    return formatted or "AI grading completed successfully."


async def _save_success_to_db(
    *,
    submission_id: int,
    grader_result: GraderResult,
) -> bool:
    rubric_result_json = grader_result.rubric_result_json
    final_grade = _coerce_final_grade(
        grader_result.final_grade,
        rubric_result_json=rubric_result_json,
    )

    student_feedback = grader_result.student_feedback
    if not isinstance(student_feedback, str) or not student_feedback.strip():
        student_feedback = _extract_summary(rubric_result_json)
    else:
        student_feedback = student_feedback.strip()

    instructor_guidance = grader_result.instructor_guidance
    if not isinstance(instructor_guidance, str) or not instructor_guidance.strip():
        instructor_guidance = _format_instructor_guidance(rubric_result_json)
    else:
        instructor_guidance = instructor_guidance.strip()

    try:
        async with async_session() as session:
            submission = await get_submission_by_id(session, submission_id)
            if not submission:
                logger.error(
                    "Submission %s not found - cannot save final result.",
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
            "Failed to persist final AI result for submission %s: %s",
            submission_id,
            exc,
        )
        return False


async def _save_failure_to_db(
    *,
    submission_id: int,
    reason: str,
) -> bool:
    failure_text = json.dumps(
        {
            "submission_id": submission_id,
            "status": "final_result_failed",
            "reason": reason,
        },
        ensure_ascii=True,
        indent=2,
    )

    try:
        async with async_session() as session:
            submission = await get_submission_by_id(session, submission_id)
            if not submission:
                logger.error(
                    "Submission %s not found - cannot persist final result failure.",
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
            "Failed to persist final result failure for submission %s: %s",
            submission_id,
            exc,
        )
        return False


async def process_final_result_job(client: JobQueue, job: Job) -> Job | None:
    del client  # Final result persistence is DB-bound, not queue-bound.

    grader_result = _get_grader_result(job)
    if not grader_result:
        logger.error("Grader result not found for Job: %s", job.job_id)
        await _save_failure_to_db(
            submission_id=job.initial_request.submission_id,
            reason="Grader result missing before final result persistence.",
        )
        return None

    if not await _save_success_to_db(
        submission_id=job.initial_request.submission_id,
        grader_result=grader_result,
    ):
        await _save_failure_to_db(
            submission_id=job.initial_request.submission_id,
            reason="Failed to persist final AI output to DB.",
        )
        return None

    job.job_result_payload.append(
        JobResultPayload(
            job_result=FinalResult(job_id=job.job_id, result=grader_result),
            finished_at=datetime.now(),
        )
    )
    job.status = JobStatus.PENDING
    return job
