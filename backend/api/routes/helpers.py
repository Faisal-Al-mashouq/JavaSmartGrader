from core.job_queue import MAIN_QUEUE, JobQueue
from schemas import JobRequest, TestCase


async def start_job_process(
    submission_id: int,
    question_id: int,
    assignment_id: int,
    student_id: int,
    image_url: str | None,
    java_code: str,
    test_cases: list[TestCase],
    rubric_json: dict,
):
    job_request = JobRequest(
        submission_id=submission_id,
        question_id=question_id,
        assignment_id=assignment_id,
        student_id=student_id,
        image_url=image_url,
        java_code=java_code,
        test_cases=test_cases,
        rubric_json=rubric_json,
    )
    await JobQueue().redis_client.lpush(MAIN_QUEUE, job_request.model_dump_json())
