import logging

from .helpers import (
    SANDBOX_TMP_DIR,
    _create_workspace,
    _extract_class_name,
    _run_execution_container,
    run_container,
)
from .schemas import (
    CompilationJobResult,
    ExecutionJobResult,
    ExecutionOutput,
    JobStatus,
    SandboxJob,
    SandboxJobResult,
    SandboxResult,
    TestCaseResult,
    TestCasesResult,
)

logger = logging.getLogger(__name__)


async def compile_job(job: SandboxJob) -> SandboxJob | None:
    class_name = _extract_class_name(job.request.java_code)
    workspace = _create_workspace(job.job_id)

    src_file = workspace / "src" / f"{class_name}.java"
    src_file.write_text(job.request.java_code)

    returncode, stdout, stderr = await run_container(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{workspace}:/workspace",
            "--memory=256m",
            "--network=none",
            "--pids-limit=50",
            "compiler-image",
            "sh",
            "/scripts/compile.sh",
            class_name,
        ]
    )

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
    class_name = _extract_class_name(job.request.java_code)
    workspace = SANDBOX_TMP_DIR / str(job.job_id)
    input_file = workspace / "input" / "input.txt"
    test_cases = (
        job.request.test_cases.test_cases
        if job.request.test_cases and job.request.test_cases.test_cases
        else None
    )
    errors = []
    outputs = []

    if not test_cases:
        input_file.write_text("")
        returncode, stdout, stderr = await _run_execution_container(
            workspace, class_name
        )
        if returncode != 0:
            errors.append(stderr)
        outputs.append(
            ExecutionOutput(
                returncode=returncode, stdout=stdout, stderr=stderr, test_case=None
            )
        )
    else:
        for test_case in test_cases:
            input_file.write_text(str(test_case.input))
            returncode, stdout, stderr = await _run_execution_container(
                workspace, class_name
            )
            if returncode != 0:
                errors.append(stderr)
            outputs.append(
                ExecutionOutput(
                    returncode=returncode,
                    stdout=stdout,
                    stderr=stderr,
                    test_case=test_case,
                )
            )

    if errors:
        logger.error(f"Execution failed for Job {job.job_id}: {errors}")
        job.result.execution_result = ExecutionJobResult(
            success=False, errors=errors, outputs=outputs
        )
        return None

    job.result.execution_result = ExecutionJobResult(
        success=True, errors=None, outputs=outputs
    )
    logger.info(f"Job {job.job_id} executed successfully")
    return job


def run_test_cases(job: SandboxJob) -> SandboxJob:
    outputs = job.result.execution_result.outputs or []
    results = []

    for output in outputs:
        if output.test_case is None:
            continue
        actual_output = (
            output.stdout.strip() if output.returncode == 0 else output.stderr.strip()
        )
        expected = str(output.test_case.expected_output).strip()
        passed = output.returncode == 0 and actual_output == expected

        results.append(
            TestCaseResult(
                input=output.test_case.input,
                expected_output=output.test_case.expected_output,
                actual_output=actual_output,
                passed=passed,
            )
        )

    job.result.test_cases_results = TestCasesResult(
        results=results if results else None
    )
    logger.info(f"Job {job.job_id} test cases evaluated")
    return job


async def set_result(job: SandboxJob, status: JobStatus) -> SandboxJobResult:
    sandbox_result = SandboxJobResult(
        job_id=job.job_id, status=status, result=job.result
    )
    return sandbox_result
