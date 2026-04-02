from core.job_queue import MAIN_QUEUE, JobQueue
from schemas import JobRequest


async def start_job_process(
    submission_id: int,
    assignment_id: int,
    student_id: int,
    image_url: str,
    java_code: str,
    rubric_json: dict,
):
    job_request = JobRequest(
        submission_id=submission_id,
        assignment_id=assignment_id,
        student_id=student_id,
        image_url=image_url,
        java_code=java_code,
        rubric_json=rubric_json,
    )
    await JobQueue().redis_client.lpush(MAIN_QUEUE, job_request.model_dump_json())
