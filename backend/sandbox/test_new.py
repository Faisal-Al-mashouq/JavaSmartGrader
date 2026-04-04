"""New unit tests for sandbox module: workspace helpers, schema validation, and edge cases."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from schemas.shared import TestCase as SchemaTestCase

from sandbox.helpers import _cleanup_workspace, _create_workspace, _extract_class_name
from sandbox.jobs import compile_job, execute_job, run_test_cases, set_result
from sandbox.schemas import (
    CompilationJobResult,
    ExecutionJobResult,
    ExecutionOutput,
    JobStatus,
    SandboxJob,
    SandboxJobRequest,
    SandboxResult,
    TestCaseResult,
)


def _run(coro):
    return asyncio.run(coro)


# --- Workspace tests ---


def test_create_workspace_creates_subdirs(tmp_path, monkeypatch):
    monkeypatch.setattr("sandbox.helpers.SANDBOX_TMP_DIR", tmp_path)
    job_id = uuid.uuid4()
    workspace = _create_workspace(job_id)
    assert (workspace / "src").is_dir()
    assert (workspace / "compiled").is_dir()
    assert (workspace / "input").is_dir()
    assert (workspace / "out").is_dir()


def test_create_workspace_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr("sandbox.helpers.SANDBOX_TMP_DIR", tmp_path)
    job_id = uuid.uuid4()
    ws1 = _create_workspace(job_id)
    (ws1 / "src" / "Test.java").write_text("hello")
    ws2 = _create_workspace(job_id)
    assert ws1 == ws2
    assert (ws2 / "src" / "Test.java").read_text() == "hello"


def test_cleanup_workspace_removes_directory(tmp_path, monkeypatch):
    monkeypatch.setattr("sandbox.helpers.SANDBOX_TMP_DIR", tmp_path)
    job_id = uuid.uuid4()
    workspace = _create_workspace(job_id)
    assert workspace.exists()
    _cleanup_workspace(job_id)
    assert not workspace.exists()


def test_cleanup_workspace_noop_if_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("sandbox.helpers.SANDBOX_TMP_DIR", tmp_path)
    job_id = uuid.uuid4()
    _cleanup_workspace(job_id)  # should not raise


# --- Class name extraction edge cases ---


@pytest.mark.parametrize(
    "code, expected",
    [
        ("public   class   SpacedName { }", "SpacedName"),
        ("/* comment */ public class InComment {}", "InComment"),
        ("public class A{}", "A"),
        ("import java.util.*;\npublic class WithImport { }", "WithImport"),
        ("Public class OcrCaps { }", "OcrCaps"),
    ],
)
def test_extract_class_name_edge_cases(code: str, expected: str) -> None:
    assert _extract_class_name(code) == expected


def test_extract_class_name_ignores_non_public_class() -> None:
    with pytest.raises(ValueError, match="public class"):
        _extract_class_name("class NotPublic { }")


def test_extract_class_name_picks_first_match() -> None:
    code = "public class First {} public class Second {}"
    assert _extract_class_name(code) == "First"


# --- Schema validation tests ---


def test_sandbox_job_request_roundtrip():
    job_id = uuid.uuid4()
    req = SandboxJobRequest(
        job_id=job_id,
        java_code="public class Main {}",
        test_cases=[SchemaTestCase(input="1", expected_output="2")],
    )
    raw = req.model_dump_json()
    restored = SandboxJobRequest.model_validate_json(raw)
    assert restored.job_id == job_id
    assert restored.java_code == "public class Main {}"
    assert len(restored.test_cases) == 1


def test_sandbox_job_request_no_test_cases():
    req = SandboxJobRequest(
        job_id=uuid.uuid4(), java_code="public class Main {}", test_cases=None
    )
    assert req.test_cases is None


def test_sandbox_result_all_none():
    result = SandboxResult(
        compilation_result=None, execution_result=None, test_cases_results=None
    )
    assert result.compilation_result is None


def test_compilation_job_result_with_errors():
    result = CompilationJobResult(success=False, errors=["error: ';' expected"])
    assert not result.success
    assert len(result.errors) == 1


def test_test_case_result_model():
    tcr = TestCaseResult(
        input="5", expected_output="10", actual_output="10", passed=True
    )
    assert tcr.passed
    assert tcr.actual_output == "10"


# --- run_test_cases additional edge cases ---


def _make_job(outputs: list[ExecutionOutput]) -> SandboxJob:
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


def test_run_test_cases_multiple_cases():
    job = _make_job(
        [
            ExecutionOutput(
                returncode=0,
                stdout="hello",
                stderr="",
                test_case=SchemaTestCase(input="a", expected_output="hello"),
            ),
            ExecutionOutput(
                returncode=0,
                stdout="world",
                stderr="",
                test_case=SchemaTestCase(input="b", expected_output="world"),
            ),
        ]
    )
    out = run_test_cases(job)
    results = out.result.test_cases_results.results
    assert len(results) == 2
    assert all(r.passed for r in results)


def test_run_test_cases_mixed_pass_fail():
    job = _make_job(
        [
            ExecutionOutput(
                returncode=0,
                stdout="correct",
                stderr="",
                test_case=SchemaTestCase(input="a", expected_output="correct"),
            ),
            ExecutionOutput(
                returncode=0,
                stdout="wrong",
                stderr="",
                test_case=SchemaTestCase(input="b", expected_output="expected"),
            ),
        ]
    )
    out = run_test_cases(job)
    results = out.result.test_cases_results.results
    assert results[0].passed is True
    assert results[1].passed is False


def test_run_test_cases_empty_outputs():
    job = _make_job([])
    out = run_test_cases(job)
    assert out.result.test_cases_results.results is None


def test_run_test_cases_nonzero_returncode_always_fails():
    job = _make_job(
        [
            ExecutionOutput(
                returncode=1,
                stdout="",
                stderr="expected_output",
                test_case=SchemaTestCase(input="x", expected_output="expected_output"),
            ),
        ]
    )
    out = run_test_cases(job)
    r = out.result.test_cases_results.results[0]
    assert r.passed is False


# --- set_result tests ---


def test_set_result_with_failed_status():
    jid = uuid.uuid4()
    job = SandboxJob(
        job_id=jid,
        status=JobStatus.RUNNING,
        created_at=datetime.now(UTC),
        request=None,
        result=SandboxResult(
            compilation_result=CompilationJobResult(
                success=False, errors=["compile error"]
            ),
            execution_result=None,
            test_cases_results=None,
        ),
    )
    wrapped = _run(set_result(job, JobStatus.FAILED))
    assert wrapped.status == JobStatus.FAILED
    assert wrapped.result.compilation_result.success is False


def test_set_result_with_error_status():
    jid = uuid.uuid4()
    job = SandboxJob(
        job_id=jid,
        status=JobStatus.RUNNING,
        created_at=datetime.now(UTC),
        request=None,
        result=None,
    )
    wrapped = _run(set_result(job, JobStatus.ERROR))
    assert wrapped.status == JobStatus.ERROR
    assert wrapped.result is None


# --- compile_job / execute_job with mocked Docker ---


def test_compile_job_success(tmp_path, monkeypatch):
    monkeypatch.setattr("sandbox.helpers.SANDBOX_TMP_DIR", tmp_path)
    monkeypatch.setattr("sandbox.jobs.SANDBOX_TMP_DIR", tmp_path)

    async def fake_run_container(cmd):
        return 0, "OK", ""

    monkeypatch.setattr("sandbox.jobs.run_container", fake_run_container)

    jid = uuid.uuid4()
    job = SandboxJob(
        job_id=jid,
        status=JobStatus.PENDING,
        created_at=datetime.now(UTC),
        request=SandboxJobRequest(
            job_id=jid,
            java_code="public class Main { public static void main(String[] a) {} }",
            test_cases=None,
        ),
        result=None,
    )
    result = _run(compile_job(job))
    assert result is not None
    assert result.result.compilation_result.success is True


def test_compile_job_failure(tmp_path, monkeypatch):
    monkeypatch.setattr("sandbox.helpers.SANDBOX_TMP_DIR", tmp_path)
    monkeypatch.setattr("sandbox.jobs.SANDBOX_TMP_DIR", tmp_path)

    async def fake_run_container(cmd):
        return 1, "", "error: ';' expected"

    monkeypatch.setattr("sandbox.jobs.run_container", fake_run_container)

    jid = uuid.uuid4()
    job = SandboxJob(
        job_id=jid,
        status=JobStatus.PENDING,
        created_at=datetime.now(UTC),
        request=SandboxJobRequest(
            job_id=jid,
            java_code="public class Main { }",
            test_cases=None,
        ),
        result=None,
    )
    result = _run(compile_job(job))
    assert result is job
    assert job.result.compilation_result.success is False
    assert "';' expected" in job.result.compilation_result.errors[0]


def test_execute_job_no_test_cases(tmp_path, monkeypatch):
    monkeypatch.setattr("sandbox.helpers.SANDBOX_TMP_DIR", tmp_path)
    monkeypatch.setattr("sandbox.jobs.SANDBOX_TMP_DIR", tmp_path)

    # Create workspace dirs
    jid = uuid.uuid4()
    ws = tmp_path / str(jid)
    (ws / "input").mkdir(parents=True)

    async def fake_exec_container(workspace, class_name):
        return 0, "Hello World", ""

    monkeypatch.setattr("sandbox.jobs._run_execution_container", fake_exec_container)

    job = SandboxJob(
        job_id=jid,
        status=JobStatus.RUNNING,
        created_at=datetime.now(UTC),
        request=SandboxJobRequest(
            job_id=jid,
            java_code="public class Main {}",
            test_cases=None,
        ),
        result=SandboxResult(
            compilation_result=CompilationJobResult(success=True, errors=None),
            execution_result=None,
            test_cases_results=None,
        ),
    )
    result = _run(execute_job(job))
    assert result is not None
    assert result.result.execution_result.success is True
    assert len(result.result.execution_result.outputs) == 1
    assert result.result.execution_result.outputs[0].stdout == "Hello World"


def test_execute_job_with_test_cases(tmp_path, monkeypatch):
    monkeypatch.setattr("sandbox.helpers.SANDBOX_TMP_DIR", tmp_path)
    monkeypatch.setattr("sandbox.jobs.SANDBOX_TMP_DIR", tmp_path)

    jid = uuid.uuid4()
    ws = tmp_path / str(jid)
    (ws / "input").mkdir(parents=True)

    call_count = 0

    async def fake_exec_container(workspace, class_name):
        nonlocal call_count
        call_count += 1
        return 0, f"output{call_count}", ""

    monkeypatch.setattr("sandbox.jobs._run_execution_container", fake_exec_container)

    job = SandboxJob(
        job_id=jid,
        status=JobStatus.RUNNING,
        created_at=datetime.now(UTC),
        request=SandboxJobRequest(
            job_id=jid,
            java_code="public class Main {}",
            test_cases=[
                SchemaTestCase(input="a", expected_output="output1"),
                SchemaTestCase(input="b", expected_output="output2"),
            ],
        ),
        result=SandboxResult(
            compilation_result=CompilationJobResult(success=True, errors=None),
            execution_result=None,
            test_cases_results=None,
        ),
    )
    result = _run(execute_job(job))
    assert result is not None
    assert result.result.execution_result.success is True
    assert len(result.result.execution_result.outputs) == 2


def test_execute_job_runtime_error(tmp_path, monkeypatch):
    monkeypatch.setattr("sandbox.helpers.SANDBOX_TMP_DIR", tmp_path)
    monkeypatch.setattr("sandbox.jobs.SANDBOX_TMP_DIR", tmp_path)

    jid = uuid.uuid4()
    ws = tmp_path / str(jid)
    (ws / "input").mkdir(parents=True)

    async def fake_exec_container(workspace, class_name):
        return 1, "", "Exception in thread"

    monkeypatch.setattr("sandbox.jobs._run_execution_container", fake_exec_container)

    job = SandboxJob(
        job_id=jid,
        status=JobStatus.RUNNING,
        created_at=datetime.now(UTC),
        request=SandboxJobRequest(
            job_id=jid,
            java_code="public class Main {}",
            test_cases=[SchemaTestCase(input="a", expected_output="x")],
        ),
        result=SandboxResult(
            compilation_result=CompilationJobResult(success=True, errors=None),
            execution_result=None,
            test_cases_results=None,
        ),
    )
    result = _run(execute_job(job))
    assert result is job
    assert job.result.execution_result.success is False
    assert "Exception in thread" in job.result.execution_result.errors[0]
