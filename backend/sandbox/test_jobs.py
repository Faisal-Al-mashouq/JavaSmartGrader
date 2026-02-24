import json
import logging
import os
import uuid

import redis
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting Test Sandbox Worker...")
    r = redis.Redis.from_url(
        os.getenv("REDIS_ENDPOINT"),
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
    r.lpush("SandboxJobQueue", payload)
    logger.info("Test job 1 pushed to SandboxJobQueue")
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
    r.lpush("SandboxJobQueue", payload2)
    logger.info("Test job 2 pushed to SandboxJobQueue")
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
    r.lpush("SandboxJobQueue", payload3)
    logger.info("Test job 3 pushed to SandboxJobQueue")
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
    r.lpush("SandboxJobQueue", payload4)
    logger.info("Test job 4 pushed to SandboxJobQueue")
