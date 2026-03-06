import json
import logging
import uuid

import redis
from settings import settings

logger = logging.getLogger(__name__)
SANDBOX_QUEUE = f"{settings.queue_namespace}:SandboxJobQueue"

if __name__ == "__main__":
    logger.info("Starting Test Sandbox Worker...")
    r = redis.Redis.from_url(
        settings.redis_endpoint,
        decode_responses=True,
    )
    payload = json.dumps(
        {
            "job_id": str(uuid.uuid4()),
            "java_code": """
            public class Main { public static void main(String[] args) {
            System.out.println(\"Hello, World!\"); } }
            """,
            "test_cases": {
                "test_cases": [{"input": "", "expected_output": "Hello, World!"}]
            },
        }
    )
    r.lpush(SANDBOX_QUEUE, payload)
    logger.info(f"Test job 1 pushed to {SANDBOX_QUEUE}")
    payload2 = json.dumps(
        {
            "job_id": str(uuid.uuid4()),
            "java_code": """public class HelloWorld {
            public static void main(String[] args) {
            System.out.println(\"Hello All World!\"); } }
            """,
            "test_cases": {
                "test_cases": [{"input": "", "expected_output": "Hello, World!"}]
            },
        }
    )
    r.lpush(SANDBOX_QUEUE, payload2)
    logger.info(f"Test job 2 pushed to {SANDBOX_QUEUE}")
    payload3 = json.dumps(
        {
            "job_id": str(uuid.uuid4()),
            "java_code": """
            import java.util.Scanner;
            public class AddNumbers {
            public static void main(String[] args) {
            Scanner scanner = new Scanner(System.in);
            int a = scanner.nextInt();
            int b = scanner.nextInt();
            System.out.println(a + b);} }
            """,
            "test_cases": {"test_cases": [{"input": "1 2", "expected_output": "3"}]},
        }
    )
    r.lpush(SANDBOX_QUEUE, payload3)
    logger.info(f"Test job 3 pushed to {SANDBOX_QUEUE}")
    payload4 = json.dumps(
        {
            "job_id": str(uuid.uuid4()),
            "java_code": """
            import java.util.Scanner;
            public class CheckEdgeTestCases {
            public static void main(String[] args) {
            Scanner scanner = new Scanner(System.in);
            if (scanner.hasNextInt()) {
            int n = scanner.nextInt();
            System.out.println(n * n);
            } else {
            System.out.println("No input provided");
            } } }
            """,
            "test_cases": {
                "test_cases": [
                    {"input": "5", "expected_output": "25"},
                    {"input": "", "expected_output": "No input provided"},
                    {"input": "3", "expected_output": "9"},
                ]
            },
        }
    )
    r.lpush(SANDBOX_QUEUE, payload4)
    logger.info(f"Test job 4 pushed to {SANDBOX_QUEUE}")
