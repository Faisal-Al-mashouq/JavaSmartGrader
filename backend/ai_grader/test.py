from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from ai_grader import main as grader_main
from ai_grader.config import Settings
from ai_grader.llm_client import LLMAPIError
from ai_grader.parser_validator import (
    JSONValidationError,
    grading_schema,
    parse_and_validate_json,
    validate_submission_id,
)
from ai_grader.prompt_builder import construct_prompt


def _run(coro):
    return asyncio.run(coro)


def _build_valid_payload(
    submission_id: int = 1,
    total_score: float = 8.5,
    max_score: float = 10.0,
) -> dict[str, Any]:
    return {
        "submission_id": submission_id,
        "total_score": total_score,
        "max_score": max_score,
        "rubric_breakdown": [
            {
                "criterion_id_or_name": "correctness",
                "earned_points": 8.5,
                "max_points": 10,
                "rationale": "Mostly correct output behavior.",
                "evidence_from_code_or_logs": "compiled_ok: True",
            }
        ],
        "feedback": {
            "summary": "Solid attempt with minor gaps.",
            "issues": [
                {
                    "location": "Line 10",
                    "description": "Edge case is not handled.",
                    "severity": "medium",
                }
            ],
            "suggestions": ["Handle null and empty inputs."],
            "next_steps": ["Add tests for boundary cases."],
        },
        "error_classification": {
            "handwriting_ocr_suspected": False,
            "syntax_or_compile": False,
            "runtime": False,
            "logic": True,
            "notes": "Logic misses one branch.",
        },
        "confidence": 0.82,
    }


def _valid_json(
    submission_id: int = 1,
    total_score: float = 8.5,
    max_score: float = 10.0,
) -> str:
    return json.dumps(
        _build_valid_payload(
            submission_id=submission_id,
            total_score=total_score,
            max_score=max_score,
        )
    )


def _sandbox_result() -> dict[str, Any]:
    return {
        "result": {
            "compilation_result": {"success": True, "errors": []},
            "execution_result": {
                "errors": [],
                "outputs": [
                    {
                        "returncode": 0,
                        "stdout": "42",
                        "stderr": "",
                        "test_case": {"input": "6 7", "expected_output": "42"},
                    }
                ],
            },
            "test_cases_results": {
                "results": [
                    {
                        "input": "6 7",
                        "expected_output": "42",
                        "actual_output": "42",
                        "passed": True,
                    }
                ]
            },
        }
    }


def _make_settings(**overrides: object) -> Settings:
    base = Settings(
        model="test-model",
        api_key="test-key",
        base_url="https://api.openai.com/v1",
        timeout_s=1.0,
        max_retries=1,
        backoff_base_s=0.01,
        backoff_max_s=0.05,
        redis_url="redis://localhost:6379",
        queue_namespace="jsg.v1",
        ai_grading_queue="AIGradingJobQueue",
        queue_poll_timeout_s=1,
        max_concurrency=1,
        temperature=0.0,
        pending_review_status="graded",
        failure_status_candidates=("failed",),
        backend_path=Path("."),
        log_level="INFO",
    )
    return base.model_copy(update=overrides)


class _DummyLLMClient:
    def __init__(self, outputs: list[object]):
        self._outputs = list(outputs)
        self.calls: list[tuple[str, int]] = []

    async def call(self, prompt: str, submission_id: int):
        self.calls.append((prompt, submission_id))
        if not self._outputs:
            raise AssertionError("No more fake LLM outputs provided")
        result = self._outputs.pop(0)
        if isinstance(result, Exception):
            raise result
        return SimpleNamespace(text=result)


def test_parser_accepts_valid_json() -> None:
    parsed = parse_and_validate_json(_valid_json(submission_id=101))
    validate_submission_id(parsed, 101)
    assert parsed["submission_id"] == 101


def test_parser_rejects_invalid_json() -> None:
    with pytest.raises(JSONValidationError):
        parse_and_validate_json("not-json")


def test_validate_submission_id_mismatch() -> None:
    parsed = parse_and_validate_json(_valid_json(submission_id=7))
    with pytest.raises(JSONValidationError):
        validate_submission_id(parsed, 9)


def test_prompt_contains_core_sections() -> None:
    schema = grading_schema()
    prompt = construct_prompt(
        submission_id=55,
        code="class Main { }",
        logs="compiled_ok: true",
        rubric={"criteria": [{"id": "correctness", "max_points": 10}]},
        schema=schema,
    )
    assert "submission_id: 55" in prompt
    assert "Student code (verbatim):" in prompt
    assert "Sandbox compile/run logs (verbatim):" in prompt
    assert "class Main { }" in prompt


def test_initialize_job_success() -> None:
    raw = json.dumps(
        {
            "job_id": "job-1",
            "submission_id": 123,
            "transcribed_text": "class Main {}",
            "sandbox_result": _sandbox_result(),
            "rubric_json": {"criteria": []},
        }
    )
    job = grader_main.initialize_job(raw)
    assert job is not None
    assert job.job_id == "job-1"
    assert job.submission_id == 123


def test_initialize_job_invalid_payloads() -> None:
    assert grader_main.initialize_job("not-json") is None
    assert grader_main.initialize_job(json.dumps(["not", "object"])) is None
    assert grader_main.initialize_job(json.dumps({"submission_id": 1})) is None


def test_format_sandbox_logs() -> None:
    logs = grader_main._format_sandbox_logs(_sandbox_result())
    assert "compiled_ok: True" in logs
    assert "case 1: returncode=0" in logs
    assert "testcase 1: input=6 7 expected=42 actual=42 passed=True" in logs


def test_parse_with_single_repair_uses_one_repair_call() -> None:
    llm_client = _DummyLLMClient(outputs=[_valid_json(submission_id=88)])
    parsed, raw_used = _run(
        grader_main._parse_with_single_repair(
            submission_id=88,
            first_response_text="bad-json",
            llm_client=llm_client,
        )
    )
    assert parsed["submission_id"] == 88
    assert raw_used == _valid_json(submission_id=88)
    assert len(llm_client.calls) == 1


def test_process_submission_success() -> None:
    llm_client = _DummyLLMClient(outputs=[_valid_json(submission_id=11)])
    job = grader_main.AIGraderJobRequest(
        job_id="job-11",
        submission_id=11,
        transcribed_text="class Main { }",
        sandbox_result=_sandbox_result(),
        rubric_json={"criteria": [{"id": "correctness", "max_points": 10}]},
    )

    result = _run(grader_main.process_submission(job=job, llm_client=llm_client))
    assert result["status"] == "COMPLETED"
    assert result["parsed_feedback"]["submission_id"] == 11


def test_process_submission_llm_error() -> None:
    llm_client = _DummyLLMClient(outputs=[LLMAPIError("boom")])
    job = grader_main.AIGraderJobRequest(
        job_id="job-12",
        submission_id=12,
        transcribed_text="class Main { }",
        sandbox_result=_sandbox_result(),
        rubric_json={"criteria": []},
    )

    result = _run(grader_main.process_submission(job=job, llm_client=llm_client))
    assert result["status"] == "FAILED"
    assert "boom" in result["error"]


def test_process_submission_parse_failure() -> None:
    llm_client = _DummyLLMClient(outputs=["bad-json", "still-bad"])
    job = grader_main.AIGraderJobRequest(
        job_id="job-13",
        submission_id=13,
        transcribed_text="class Main { }",
        sandbox_result=_sandbox_result(),
        rubric_json={"criteria": []},
    )

    result = _run(grader_main.process_submission(job=job, llm_client=llm_client))
    assert result["status"] == "FAILED"
    assert result["raw_output"] == "bad-json"


def test_build_completion_payload_success() -> None:
    job = grader_main.AIGraderJobRequest(
        job_id="job-21",
        submission_id=21,
        transcribed_text="",
        sandbox_result=None,
        rubric_json={},
    )
    outcome = {
        "status": "COMPLETED",
        "parsed_feedback": {
            "total_score": 9,
            "feedback": {"summary": "Nice work."},
        },
    }
    payload = grader_main._build_completion_payload(job=job, outcome=outcome)
    assert payload["status"] == "COMPLETED"
    assert payload["final_grade"] == pytest.approx(9.0)
    assert payload["student_feedback"] == "Nice work."


def test_build_completion_payload_failure() -> None:
    job = grader_main.AIGraderJobRequest(
        job_id="job-22",
        submission_id=22,
        transcribed_text="",
        sandbox_result=None,
        rubric_json={},
    )
    payload = grader_main._build_completion_payload(
        job=job,
        outcome={"status": "FAILED", "error": "bad output", "raw_output": "{x}"},
    )
    assert payload["status"] == "FAILED"
    assert payload["error"] == "bad output"
    assert payload["raw_output"] == "{x}"


def test_main_loop_once_no_job() -> None:
    class _FakeRedis:
        def __init__(self) -> None:
            self.claim_calls = 0

        async def brpoplpush(self, src: str, dst: str, timeout: int):
            self.claim_calls += 1
            return None

        async def lrem(self, queue_name: str, count: int, payload: str) -> None:
            return None

        async def lpush(self, queue_name: str, payload: str) -> None:
            return None

    client = SimpleNamespace(redis_client=_FakeRedis(), max_concurrency=1)
    settings = _make_settings(queue_poll_timeout_s=0)
    llm_client = _DummyLLMClient(outputs=[])

    _run(
        grader_main.main_loop(
            client,
            settings=settings,
            llm_client=llm_client,
            process_id=0,
            once=True,
        )
    )
    assert client.redis_client.claim_calls == 1


def test_main_loop_removes_invalid_payload_from_processing() -> None:
    class _FakeRedis:
        def __init__(self) -> None:
            self.removed: tuple[str, int, str] | None = None
            self._returned = False

        async def brpoplpush(self, src: str, dst: str, timeout: int):
            if self._returned:
                return None
            self._returned = True
            return "not-json"

        async def lrem(self, queue_name: str, count: int, payload: str) -> None:
            self.removed = (queue_name, count, payload)

        async def lpush(self, queue_name: str, payload: str) -> None:
            return None

    client = SimpleNamespace(redis_client=_FakeRedis(), max_concurrency=1)
    settings = _make_settings(queue_poll_timeout_s=0)
    llm_client = _DummyLLMClient(outputs=[])

    _run(
        grader_main.main_loop(
            client,
            settings=settings,
            llm_client=llm_client,
            process_id=0,
            once=True,
        )
    )

    assert client.redis_client.removed is not None
    queue_name, count, payload = client.redis_client.removed
    assert (
        queue_name
        == f"{settings.queue_namespace}:{settings.ai_grading_queue}:processing"
    )
    assert count == 1
    assert payload == "not-json"


def test_main_loop_processes_one_job_and_publishes_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_job = json.dumps(
        {
            "job_id": "job-31",
            "submission_id": 31,
            "transcribed_text": "class Main {}",
            "sandbox_result": _sandbox_result(),
            "rubric_json": {"criteria": []},
        }
    )

    class _FakeRedis:
        def __init__(self) -> None:
            self.pushed: list[tuple[str, str]] = []
            self.removed: list[tuple[str, int, str]] = []
            self._returned = False

        async def brpoplpush(self, src: str, dst: str, timeout: int):
            if self._returned:
                return None
            self._returned = True
            return raw_job

        async def lpush(self, queue_name: str, payload: str) -> None:
            self.pushed.append((queue_name, payload))

        async def lrem(self, queue_name: str, count: int, payload: str) -> None:
            self.removed.append((queue_name, count, payload))

    async def _fake_process_job(*, job, llm_client):
        return {
            "job_id": job.job_id,
            "submission_id": job.submission_id,
            "status": "COMPLETED",
            "rubric_result_json": {"total_score": 10},
        }

    monkeypatch.setattr(grader_main, "process_job", _fake_process_job)

    client = SimpleNamespace(redis_client=_FakeRedis(), max_concurrency=1)
    settings = _make_settings(queue_poll_timeout_s=0)
    llm_client = _DummyLLMClient(outputs=[])

    _run(
        grader_main.main_loop(
            client,
            settings=settings,
            llm_client=llm_client,
            process_id=0,
            once=True,
        )
    )

    assert len(client.redis_client.pushed) == 1
    completion_queue, completion_payload = client.redis_client.pushed[0]
    assert (
        completion_queue
        == f"{settings.queue_namespace}:{settings.ai_grading_queue}:completed:job-31"
    )
    parsed_payload = json.loads(completion_payload)
    assert parsed_payload["status"] == "COMPLETED"

    assert len(client.redis_client.removed) == 1
    removed_queue, removed_count, removed_payload = client.redis_client.removed[0]
    assert (
        removed_queue
        == f"{settings.queue_namespace}:{settings.ai_grading_queue}:processing"
    )
    assert removed_count == 1
    assert removed_payload == raw_job


def test_run_worker_once_uses_main_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    observed = {"called": False, "once": None}

    class _FakeRedis:
        async def aclose(self) -> None:
            return None

    class _FakeWorker:
        def __init__(self, *, redis_url: str, max_concurrency: int):
            self.redis_client = _FakeRedis()
            self.max_concurrency = max_concurrency

    async def _fake_main_loop(
        client,
        *,
        settings: Settings,
        llm_client,
        process_id: int = 0,
        once: bool = False,
    ) -> None:
        observed["called"] = True
        observed["once"] = once

    class _FakeLLM:
        def __init__(self, settings: Settings):
            self.settings = settings

    monkeypatch.setattr(grader_main, "AIGraderWorker", _FakeWorker)
    monkeypatch.setattr(grader_main, "main_loop", _fake_main_loop)
    monkeypatch.setattr(grader_main, "LLMClient", _FakeLLM)

    _run(grader_main.run_worker(settings=_make_settings(), once=True))
    assert observed["called"] is True
    assert observed["once"] is True


def test_start_loads_settings_and_runs_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed = {"settings": None}
    expected_settings = _make_settings()

    def _fake_load_settings() -> Settings:
        return expected_settings

    async def _fake_run_worker(*, settings: Settings, once: bool = False) -> None:
        observed["settings"] = settings
        assert once is False

    monkeypatch.setattr(grader_main, "load_settings", _fake_load_settings)
    monkeypatch.setattr(grader_main, "run_worker", _fake_run_worker)

    _run(grader_main.start())
    assert observed["settings"] is expected_settings
