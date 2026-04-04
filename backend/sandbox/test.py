from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime

import pytest
from schemas.shared import TestCase as SchemaTestCase

from sandbox.helpers import _extract_class_name
from sandbox.jobs import run_test_cases, set_result
from sandbox.sandbox_worker import initialize_job
from sandbox.schemas import (
    ExecutionJobResult,
    ExecutionOutput,
    JobStatus,
    SandboxJob,
    SandboxJobRequest,
    SandboxJobResult,
    SandboxResult,
)


def _run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize(
    "code, expected",
    [
        ("public class Main { }", "Main"),
        (
            "package x;\npublic class HelloWorld {\n}",
            "HelloWorld",
        ),
    ],
)
def test_extract_class_name(code: str, expected: str) -> None:
    assert _extract_class_name(code) == expected


def test_extract_class_name_raises_when_missing() -> None:
    with pytest.raises(ValueError, match="public class"):
        _extract_class_name("// no class here")


def test_initialize_job_parses_valid_payload() -> None:
    job_id = uuid.uuid4()
    raw = json.dumps(
        {
            "job_id": str(job_id),
            "java_code": "public class Main { public static void main(String[] a) {} }",
            "test_cases": [{"input": "", "expected_output": "ok"}],
        }
    )

    job = _run(initialize_job(raw))
    assert job is not None
    assert job.job_id == job_id
    assert job.status == JobStatus.PENDING
    assert isinstance(job.request, SandboxJobRequest)


def test_initialize_job_returns_none_on_invalid_json() -> None:
    assert _run(initialize_job("not-json")) is None


def test_initialize_job_returns_none_on_schema_mismatch() -> None:
    raw = json.dumps({"job_id": "not-a-uuid", "java_code": "x"})
    assert _run(initialize_job(raw)) is None


def _job_with_execution_outputs(
    outputs: list[ExecutionOutput],
) -> SandboxJob:
    jid = uuid.uuid4()
    return SandboxJob(
        job_id=jid,
        status=JobStatus.RUNNING,
        created_at=datetime.now(UTC),
        request=SandboxJobRequest(
            job_id=jid,
            java_code="public class Main {}",
            test_cases=[SchemaTestCase(input="1", expected_output="1")],
        ),
        result=SandboxResult(
            compilation_result=None,
            execution_result=ExecutionJobResult(
                success=True, errors=None, outputs=outputs
            ),
            test_cases_results=None,
        ),
    )


def test_run_test_cases_marks_pass_when_stdout_matches() -> None:
    job = _job_with_execution_outputs(
        [
            ExecutionOutput(
                returncode=0,
                stdout="  hello  ",
                stderr="",
                test_case=SchemaTestCase(input="x", expected_output="hello"),
            )
        ]
    )
    out = run_test_cases(job)
    assert out.result.test_cases_results is not None
    assert out.result.test_cases_results.results is not None
    assert len(out.result.test_cases_results.results) == 1
    r = out.result.test_cases_results.results[0]
    assert r.passed is True
    assert r.actual_output == "hello"


def test_run_test_cases_marks_fail_on_mismatch() -> None:
    job = _job_with_execution_outputs(
        [
            ExecutionOutput(
                returncode=0,
                stdout="wrong",
                stderr="",
                test_case=SchemaTestCase(input="", expected_output="right"),
            )
        ]
    )
    out = run_test_cases(job)
    r = out.result.test_cases_results.results[0]
    assert r.passed is False


def test_run_test_cases_uses_stderr_when_nonzero_return() -> None:
    job = _job_with_execution_outputs(
        [
            ExecutionOutput(
                returncode=1,
                stdout="ignored",
                stderr="  err  ",
                test_case=SchemaTestCase(input="", expected_output="err"),
            )
        ]
    )
    out = run_test_cases(job)
    r = out.result.test_cases_results.results[0]
    assert r.actual_output == "err"
    assert r.passed is False


def test_run_test_cases_skips_outputs_without_test_case() -> None:
    job = _job_with_execution_outputs(
        [
            ExecutionOutput(
                returncode=0,
                stdout="a",
                stderr="",
                test_case=None,
            )
        ]
    )
    out = run_test_cases(job)
    assert out.result.test_cases_results.results is None


def test_set_result_builds_sandbox_job_result() -> None:
    jid = uuid.uuid4()
    job = SandboxJob(
        job_id=jid,
        status=JobStatus.RUNNING,
        created_at=datetime.now(UTC),
        request=None,
        result=SandboxResult(
            compilation_result=None, execution_result=None, test_cases_results=None
        ),
    )

    async def _go() -> SandboxJobResult:
        return await set_result(job, JobStatus.COMPLETED)

    wrapped = _run(_go())
    assert wrapped.job_id == jid
    assert wrapped.status == JobStatus.COMPLETED
    assert wrapped.result is job.result
