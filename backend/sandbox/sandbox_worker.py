import asyncio
import datetime
import logging
import os
import re
import shutil
import uuid
from pathlib import Path

import redis.asyncio as redis
from dotenv import load_dotenv

from backend.sandbox.schemas import (
    SandboxJobRequest,
    SandboxJob,
    SandboxJobResult,
    SandboxResult,
    CompilationJobResult,
    ExecutionJobResult,
    TestCaseResult,
    TestCasesResult,
    JobStatus
)

load_dotenv()
logger = logging.getLogger(__name__)
SANDBOX_TMP_DIR = Path(__file__).parent / "tmp"


class Sandbox:
    def __init__(self, redis_url: str, max_concurrency: int = 4):
        self.max_concurrency = max_concurrency
        self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)


def extract_class_name(java_code: str) -> str:
    match = re.search(r"public\s+class\s+(\w+)", java_code)
    if not match:
        raise ValueError("Could not find public class name in Java code")
    return match.group(1)


def create_workspace(job_id: uuid.UUID) -> Path:
    workspace = SANDBOX_TMP_DIR / str(job_id)
    (workspace / "src").mkdir(parents=True, exist_ok=True)
    (workspace / "compiled").mkdir(exist_ok=True)
    (workspace / "input").mkdir(exist_ok=True)
    (workspace / "out").mkdir(exist_ok=True)
    return workspace


def cleanup_workspace(job_id: uuid.UUID):
    workspace = SANDBOX_TMP_DIR / str(job_id)
    if workspace.exists():
        shutil.rmtree(workspace)


async def run_container(cmd: list[str]) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode(), stderr.decode()


async def start():
    client = Sandbox(os.getenv("REDIS_ENDPOINT"), max_concurrency=4)
    logger.info("Sandbox Worker started")
    await asyncio.gather(*(main_loop(client) for _ in range(client.max_concurrency)))


async def main_loop(client: Sandbox):
    while True:
        result = await client.redis_client.blpop("SandboxJobQueue", timeout=0)
        logger.info(f"SandboxJob received: {result}")
        if result:
            _, job_request = result
            
            initialized_job = await initialize_job(job_request)
            if not initialized_job:
                logger.error("Failed to initialize job, skipping")
                continue
            
            processed_job = await process_job(initialized_job)
            if processed_job.status != JobStatus.COMPLETED:
                logger.error("Failed to process job, skipping")
                continue

            await save_result(processed_job)


async def initialize_job(job_request: str) -> SandboxJob | None:
    logger.info(f"Initializing Job request: {job_request}")
    try:
        sandbox_job_request = SandboxJobRequest.model_validate_json(job_request)
        job = SandboxJob(
            job_id=sandbox_job_request.job_id,
            status=JobStatus.PENDING,
            created_at=datetime.datetime.now(),
            request=sandbox_job_request,
            result=None
        )
        logger.info(f"Job initialized successfully: {job.job_id}")
        return job
    except Exception as e:
        logger.error(f"Failed to initialize job: {e}")
        return None


async def process_job(job: SandboxJob) -> SandboxJobResult:
    logger.info(f"Processing Job: {job.job_id}")
    try:
        logger.info(f"Job {job.job_id} compilation started")    
        compiled_job = await compile_job(job)
        if not compiled_job:
            logger.error(f"Compilation failed for Job: {job.job_id}")
            return await set_result(job, JobStatus.FAILED)
        
        logger.info(f"Job {job.job_id} execution started")
        executed_job = await execute_job(compiled_job)
        if not executed_job:
            logger.error(f"Execution failed for Job: {job.job_id}")
            return await set_result(compiled_job, JobStatus.FAILED)
        
        logger.info(f"Job {job.job_id} test cases execution started")
        tested_job = await run_test_cases(executed_job)
        if not tested_job:
            logger.error(f"Test cases failed for Job: {job.job_id}")
            return await set_result(executed_job, JobStatus.FAILED)
    
        logger.info(f"Job {job.job_id} completed successfully")
        return await set_result(tested_job, JobStatus.COMPLETED)
    
    except Exception as e:
        logger.error(f"SandboxJob error: {e}")
        return await set_result(job, JobStatus.FAILED)
    finally:
        cleanup_workspace(job.job_id)


async def compile_job(job: SandboxJob) -> SandboxJob | None:
    class_name = extract_class_name(job.request.java_code)
    workspace = create_workspace(job.job_id)

    src_file = workspace / "src" / f"{class_name}.java"
    src_file.write_text(job.request.java_code)

    returncode, stdout, stderr = await run_container([
        "docker", "run", "--rm",
        "-v", f"{workspace}:/workspace",
        "--memory=256m", "--network=none", "--pids-limit=50",
        "compiler-image", "sh", "/scripts/compile.sh", class_name
    ])

    if returncode != 0:
        logger.error(f"Compilation failed for Job {job.job_id}: {stderr}")
        job.result = SandboxResult(
            compilation_result=CompilationJobResult(success=False, errors=[stderr]),
            execution_result=None,
            test_cases_results=None,
        )
        return None

    job.result = SandboxResult(
        compilation_result=CompilationJobResult(success=True, errors=None),
        execution_result=None,
        test_cases_results=None,
    )
    logger.info(f"Job {job.job_id} compiled successfully")
    return job


async def execute_job(job: SandboxJob) -> SandboxJob | None:
    class_name = extract_class_name(job.request.java_code)
    workspace = SANDBOX_TMP_DIR / str(job.job_id)

    input_file = workspace / "input" / "input.txt"
    input_file.write_text("")

    returncode, stdout, stderr = await run_container([
        "docker", "run", "--rm",
        "-v", f"{workspace}:/workspace",
        "--memory=256m", "--network=none", "--pids-limit=50", "--read-only",
        "executer-image", "sh", "/scripts/execute.sh", class_name
    ])

    if returncode != 0:
        logger.error(f"Execution failed for Job {job.job_id}: {stderr}")
        job.result.execution_result = ExecutionJobResult(success=False, errors=[stderr])
        return None

    job.result.execution_result = ExecutionJobResult(success=True, errors=None)
    logger.info(f"Job {job.job_id} executed successfully")
    return job


async def run_test_cases(job: SandboxJob) -> SandboxJob | None:
    if not job.request.test_cases or not job.request.test_cases.test_cases:
        job.result.test_cases_results = TestCasesResult(results=None)
        logger.info(f"Job {job.job_id} has no test cases, skipping")
        return job

    class_name = extract_class_name(job.request.java_code)
    workspace = SANDBOX_TMP_DIR / str(job.job_id)
    input_file = workspace / "input" / "input.txt"
    results = []

    for test_case in job.request.test_cases.test_cases:
        input_file.write_text(str(test_case.input))

        returncode, stdout, stderr = await run_container([
            "docker", "run", "--rm",
            "-v", f"{workspace}:/workspace",
            "--memory=256m", "--network=none", "--pids-limit=50", "--read-only",
            "executer-image", "sh", "/scripts/execute.sh", class_name
        ])

        actual_output = stdout.strip() if returncode == 0 else stderr.strip()
        expected = str(test_case.expected_output).strip()
        passed = returncode == 0 and actual_output == expected

        results.append(TestCaseResult(
            input=test_case.input,
            expected_output=test_case.expected_output,
            actual_output=actual_output,
            passed=passed,
        ))

    job.result.test_cases_results = TestCasesResult(results=results)
    logger.info(f"Job {job.job_id} test cases executed successfully")
    return job


async def set_result(job: SandboxJob, status: JobStatus) -> SandboxJobResult:
    sandbox_result = SandboxJobResult(
        job_id=job.job_id,
        status=status,
        result=job.result
    )
    return sandbox_result


async def save_result(job: SandboxJobResult):
    # Placeholder for result saving logic (e.g., storing in Redis, database)
    logger.info(f"Job result saved successfully")


if __name__ == "__main__":
    asyncio.run(start())
