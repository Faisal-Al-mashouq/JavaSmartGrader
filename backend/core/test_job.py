import asyncio

from redis.asyncio import Redis
from schemas import JobRequest, TestCase
from settings import settings

MAIN_QUEUE = f"{settings.queue_namespace}:MainJobQueue"

job = JobRequest(
    submission_id=1,
    question_id=1,
    assignment_id=1,
    student_id=1,
    image_url="https://example.com/image.jpg",
    java_code="""
    public class Main {
    public static void main(String[] args) {
    System.out.println("Hello, World!");
    }
    }
    """,
    test_cases=[TestCase(input=" ", expected_output="Hello, World!")],
    rubric_json={
        "criteria": {
            "Correctness": {
                "weight": 100,
                "description": "The submission is correct.",
            },
        }
    },
)


async def main() -> None:
    r = Redis.from_url(settings.redis_endpoint, decode_responses=True)
    try:
        await r.lpush(MAIN_QUEUE, job.model_dump_json())
    finally:
        await r.aclose()


if __name__ == "__main__":
    asyncio.run(main())
