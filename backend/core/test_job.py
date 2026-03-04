import asyncio
from datetime import datetime

from redis.asyncio import Redis
from schemas import JobRequest, JobType, SubmissionPayload, TestCase
from settings import settings

job = JobRequest(
    type=JobType.SUBMISSION,
    payload=SubmissionPayload(
        type=JobType.SUBMISSION,
        submission_id=1,
        question_id=1,
        assignment_id=1,
        student_id=1,
        image_url="https://example.com/image.jpg",
        test_cases=[TestCase(input="", expected_output="")],
        rubric_json={
            "criteria": {
                "Correctness": {
                    "weight": 100,
                    "description": "The submission is correct.",
                },
            }
        },
        created_at=datetime.now(),
    ),
)


async def main() -> None:
    r = Redis.from_url(settings.redis_endpoint, decode_responses=True)
    try:
        await r.lpush("MainJobQueue", job.model_dump_json())
    finally:
        await r.aclose()


if __name__ == "__main__":
    asyncio.run(main())
