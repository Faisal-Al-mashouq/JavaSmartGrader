from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from ai_grader import main as grader_main
from ai_grader.adapters import database_adapter as db_module
from ai_grader.adapters import queue_adapter as queue_module
from ai_grader.config import Settings, load_settings
from ai_grader.llm_client import LLMAPIError, LLMClient
from ai_grader.parser_validator import (
    JSONValidationError,
    grading_schema,
    parse_and_validate_json,
    validate_submission_id,
)
from ai_grader.prompt_builder import construct_prompt


def _run(coro: Awaitable[object]) -> object:
    return asyncio.run(coro)


async def _async_noop() -> None:
    fut = asyncio.get_running_loop().create_future()
    fut.set_result(None)
    await fut


def _build_valid_payload(
    submission_id: int = 1,
    total_score: float = 8.5,
    max_score: float = 10.0,
) -> dict:
    return {
        "submission_id": submission_id,
        "total_score": total_score,
        "max_score": max_score,
        "rubric_breakdown": [
            {
                "criterion_id_or_name": "Compilation",
                "earned_points": 3,
                "max_points": 4,
                "rationale": "One warning but successful compile.",
                "evidence_from_code_or_logs": "compiled_ok: true",
            }
        ],
        "feedback": {
            "summary": "Solid attempt with minor edge-case issue.",
            "issues": [
                {
                    "location": "Line 14",
                    "description": "Null input not handled.",
                    "severity": "medium",
                }
            ],
            "suggestions": ["Add null checks before parsing input."],
            "next_steps": ["Run tests with empty and null-like inputs."],
        },
        "error_classification": {
            "handwriting_ocr_suspected": False,
            "syntax_or_compile": False,
            "runtime": False,
            "logic": True,
            "notes": "Edge-case handling appears incomplete.",
        },
        "confidence": 0.81,
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
        ready_queue_name="jsg.v1:Ready_Grading",
        queue_poll_timeout_s=1,
        temperature=0.2,
        pending_review_status="Pending_Review",
        failure_status_candidates=("Grading_Failed",),
        backend_path=Path("."),
    )
    return base.model_copy(update=overrides)


def _patch_async_client(
    monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport
) -> None:
    original = httpx.AsyncClient

    class PatchedAsyncClient(original):
        def __init__(self, *args: object, **kwargs: object) -> None:
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", PatchedAsyncClient)


def test_parser_accepts_valid_json() -> None:
    parsed = parse_and_validate_json(
        _valid_json(submission_id=101, total_score=8.5, max_score=10)
    )
    validate_submission_id(parsed, 101)
    assert float(parsed["total_score"]) == pytest.approx(8.5)


def test_parser_rejects_incomplete_json() -> None:
    bad_json = json.dumps({"submission_id": 3})
    with pytest.raises(JSONValidationError):
        parse_and_validate_json(bad_json)


def test_prompt_contains_verbatim_sections() -> None:
    schema = grading_schema()
    prompt = construct_prompt(
        submission_id=42,
        code="class Main { public static void main(String[] args) {} }",
        logs="compiled_ok: true\nruntime_output:\nHello",
        rubric={"criteria": [{"name": "Correctness", "points": 10}]},
        schema=schema,
    )
    assert "Return ONLY valid JSON matching schema" in prompt
    assert "class Main" in prompt
    assert "compiled_ok: true" in prompt
    assert '"Correctness"' in prompt


def test_build_chat_completions_url_normalizes() -> None:
    assert (
        LLMClient._build_chat_completions_url("https://api.openai.com/v1")
        == "https://api.openai.com/v1/chat/completions"
    )
    assert (
        LLMClient._build_chat_completions_url("https://api.openai.com/v1/")
        == "https://api.openai.com/v1/chat/completions"
    )
    assert (
        LLMClient._build_chat_completions_url(
            "https://api.openai.com/v1/chat/completions"
        )
        == "https://api.openai.com/v1/chat/completions"
    )


def test_llm_client_requires_api_key() -> None:
    settings = _make_settings(api_key="")
    client = LLMClient(settings)
    with pytest.raises(LLMAPIError):
        _run(client.call("prompt", submission_id=1))


def test_llm_client_retries_on_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = {"count": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        call_count["count"] += 1
        if call_count["count"] == 1:
            return httpx.Response(500, json={"error": "server error"})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"ok": true}'}}]},
        )

    transport = httpx.MockTransport(handler)
    _patch_async_client(monkeypatch, transport)

    async def _no_sleep(_: float) -> None:
        await _async_noop()

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    settings = _make_settings(max_retries=1)
    client = LLMClient(settings)
    response = _run(client.call("prompt", submission_id=1))
    assert response.attempt_count == 2
    assert call_count["count"] == 2


def test_llm_client_non_retryable_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "bad request"})

    transport = httpx.MockTransport(handler)
    _patch_async_client(monkeypatch, transport)

    settings = _make_settings(max_retries=2)
    client = LLMClient(settings)
    with pytest.raises(LLMAPIError):
        _run(client.call("prompt", submission_id=2))


def test_llm_client_invalid_json_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json")

    transport = httpx.MockTransport(handler)
    _patch_async_client(monkeypatch, transport)

    client = LLMClient(_make_settings())
    with pytest.raises(LLMAPIError):
        _run(client.call("prompt", submission_id=3))


def test_llm_client_missing_choices(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "no-choices"})

    transport = httpx.MockTransport(handler)
    _patch_async_client(monkeypatch, transport)

    client = LLMClient(_make_settings())
    with pytest.raises(LLMAPIError):
        _run(client.call("prompt", submission_id=4))


def test_llm_client_sends_expected_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"ok": true}'}}]},
        )

    transport = httpx.MockTransport(handler)
    _patch_async_client(monkeypatch, transport)

    settings = _make_settings(model="m1", temperature=0.4)
    client = LLMClient(settings)
    _run(client.call("PROMPT", submission_id=5))

    headers = captured["headers"]
    payload = captured["payload"]
    assert headers["authorization"] == "Bearer test-key"
    assert payload["model"] == "m1"
    assert payload["temperature"] == pytest.approx(0.4)
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["content"] == "PROMPT"


def test_extract_text_handles_list_content() -> None:
    response_json = {
        "choices": [{"message": {"content": [{"text": "Hello, "}, {"text": "world!"}]}}]
    }
    assert LLMClient._extract_text(response_json) == "Hello, world!"


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


class _DummyDBAdapter:
    def __init__(self) -> None:
        self.saved_feedback: tuple[int, dict] | None = None
        self.updated_status: tuple[int, str] | None = None
        self.failure_feedback: tuple[int, str, str] | None = None
        self.failure_marked: tuple[int, tuple[str, ...]] | None = None
        self.transcription = "class Main {}"
        self.logs = "compiled_ok: true"
        self.rubric = {"criteria": [{"name": "Correctness", "points": 10}]}

    async def get_transcription(self, submission_id: int) -> str:
        return self.transcription

    async def get_sandbox_results(self, submission_id: int) -> str:
        return self.logs

    async def get_rubric(self, submission_id: int):
        return self.rubric

    async def save_feedback(self, submission_id: int, parsed_feedback: dict) -> None:
        self.saved_feedback = (submission_id, parsed_feedback)

    async def persist_failure_feedback(
        self, submission_id: int, reason: str, raw_output: str
    ) -> None:
        self.failure_feedback = (submission_id, reason, raw_output)

    async def update_status(self, submission_id: int, new_status: str) -> bool:
        self.updated_status = (submission_id, new_status)
        return True

    async def mark_failure_status(
        self, submission_id: int, candidates: tuple[str, ...]
    ) -> bool:
        self.failure_marked = (submission_id, candidates)
        return True


def test_parse_with_single_repair_no_repair_needed() -> None:
    llm_client = _DummyLLMClient(outputs=[])
    raw_json = _valid_json(submission_id=7)
    parsed, raw_used = _run(
        grader_main._parse_with_single_repair(
            submission_id=7,
            first_response_text=raw_json,
            llm_client=llm_client,
        )
    )
    assert raw_used == raw_json
    assert parsed["submission_id"] == 7
    assert llm_client.calls == []


def test_parse_with_single_repair_uses_repair() -> None:
    repair_json = _valid_json(submission_id=9)
    llm_client = _DummyLLMClient(outputs=[repair_json])
    parsed, raw_used = _run(
        grader_main._parse_with_single_repair(
            submission_id=9,
            first_response_text="not-json",
            llm_client=llm_client,
        )
    )
    assert raw_used == repair_json
    assert parsed["submission_id"] == 9
    assert len(llm_client.calls) == 1


def test_process_submission_success() -> None:
    db_adapter = _DummyDBAdapter()
    llm_client = _DummyLLMClient(outputs=[_valid_json(submission_id=11)])
    settings = _make_settings()

    result = _run(
        grader_main.process_submission(
            submission_id=11,
            db_adapter=db_adapter,
            llm_client=llm_client,
            settings=settings,
            payload_inputs={
                "code": "class Main {}",
                "logs": "compiled_ok: true",
                "rubric": {"criteria": [{"name": "Correctness", "points": 10}]},
            },
        )
    )

    assert result["status"] == "COMPLETED"
    assert db_adapter.saved_feedback is not None
    assert db_adapter.updated_status == (11, settings.pending_review_status)


def test_process_submission_llm_error() -> None:
    db_adapter = _DummyDBAdapter()
    llm_client = _DummyLLMClient(outputs=[LLMAPIError("boom")])
    settings = _make_settings()

    result = _run(
        grader_main.process_submission(
            submission_id=12,
            db_adapter=db_adapter,
            llm_client=llm_client,
            settings=settings,
            payload_inputs={"code": "x", "logs": "y", "rubric": {}},
        )
    )

    assert result["status"] == "FAILED"
    assert db_adapter.saved_feedback is None


def test_process_submission_parse_failure_persists() -> None:
    db_adapter = _DummyDBAdapter()
    llm_client = _DummyLLMClient(outputs=["bad-json", "still-bad"])
    settings = _make_settings()

    result = _run(
        grader_main.process_submission(
            submission_id=13,
            db_adapter=db_adapter,
            llm_client=llm_client,
            settings=settings,
            payload_inputs={"code": "x", "logs": "y", "rubric": {}},
        )
    )

    assert result["status"] == "FAILED"
    assert result.get("raw_output") == "bad-json"
    assert db_adapter.failure_feedback is not None
    assert db_adapter.failure_marked is not None


def test_build_completion_payload_completed() -> None:
    job = queue_module.QueueJob(
        submission_id=5,
        job_id="job-5",
        raw_payload="{}",
        queue_name="queue",
    )
    outcome = {
        "status": "COMPLETED",
        "parsed_feedback": {
            "total_score": 9,
            "feedback": {"summary": "Nice job."},
        },
    }
    payload = grader_main._build_completion_payload(job=job, outcome=outcome)
    assert payload["status"] == "COMPLETED"
    assert payload["final_grade"] == pytest.approx(9.0)
    assert payload["student_feedback"] == "Nice job."


def test_build_completion_payload_failed() -> None:
    job = queue_module.QueueJob(
        submission_id=6,
        job_id="job-6",
        raw_payload="{}",
        queue_name="queue",
    )
    outcome = {"status": "FAILED", "error": "boom", "raw_output": "bad"}
    payload = grader_main._build_completion_payload(job=job, outcome=outcome)
    assert payload["status"] == "FAILED"
    assert payload["error"] == "boom"
    assert payload["raw_output"] == "bad"


def test_coerce_lines() -> None:
    assert grader_main._coerce_lines(None) == ""
    assert grader_main._coerce_lines(["a", 2]) == "a\n2"
    assert grader_main._coerce_lines(123) == "123"


def test_format_sandbox_logs() -> None:
    sandbox_result = {
        "result": {
            "compilation_result": {"success": True, "errors": ""},
            "execution_result": {
                "errors": "",
                "outputs": [
                    {
                        "returncode": 0,
                        "stdout": "Hello",
                        "stderr": "",
                        "test_case": {
                            "input": "1",
                            "expected_output": "1",
                        },
                    }
                ],
            },
            "test_cases_results": {
                "results": [
                    {
                        "input": "1",
                        "expected_output": "1",
                        "actual_output": "1",
                        "passed": True,
                    }
                ]
            },
        }
    }
    formatted = grader_main._format_sandbox_logs(sandbox_result)
    assert "compiled_ok: True" in formatted
    assert "case 1: returncode=0" in formatted
    assert "testcase 1: input=1 expected=1 actual=1 passed=True" in formatted


def test_payload_inputs_from_raw() -> None:
    assert grader_main._payload_inputs_from_raw("not-json") is None
    assert grader_main._payload_inputs_from_raw(json.dumps([1, 2])) is None
    assert grader_main._payload_inputs_from_raw(json.dumps({"x": 1})) is None

    payload = {
        "transcribed_text": "class Main {}",
        "rubric_json": {"criteria": []},
        "sandbox_result": {"result": {"compilation_result": {"success": True}}},
    }
    parsed = grader_main._payload_inputs_from_raw(json.dumps(payload))
    assert parsed is not None
    assert parsed["code"] == "class Main {}"
    assert parsed["rubric"] == {"criteria": []}
    assert "compiled_ok" in parsed["logs"]


def test_extract_submission_id_variants() -> None:
    assert queue_module.RedisQueueAdapter._extract_submission_id("123") == 123
    assert (
        queue_module.RedisQueueAdapter._extract_submission_id(
            json.dumps({"submission_id": "456"})
        )
        == 456
    )
    assert (
        queue_module.RedisQueueAdapter._extract_submission_id(json.dumps({"id": 7}))
        == 7
    )
    assert (
        queue_module.RedisQueueAdapter._extract_submission_id(
            json.dumps({"submission": {"id": "8"}})
        )
        == 8
    )
    with pytest.raises(ValueError):
        queue_module.RedisQueueAdapter._extract_submission_id("not-json")


def test_extract_job_id() -> None:
    assert (
        queue_module.RedisQueueAdapter._extract_job_id(json.dumps({"job_id": 9})) == "9"
    )
    assert queue_module.RedisQueueAdapter._extract_job_id("not-json") is None
    assert queue_module.RedisQueueAdapter._extract_job_id(json.dumps([1])) is None


def test_redis_queue_adapter_dequeue_uses_brpoplpush() -> None:
    class _FakeRedis:
        def __init__(self) -> None:
            self.claim_args: tuple[str, str, int] | None = None

        async def brpoplpush(self, src: str, dst: str, timeout: int):
            self.claim_args = (src, dst, timeout)
            return json.dumps({"submission_id": 17, "job_id": "job-17"})

    adapter = object.__new__(queue_module.RedisQueueAdapter)
    adapter._redis = _FakeRedis()
    adapter._poll_timeout_s = 7

    job = _run(adapter.dequeue("jsg.v1:Ready_Grading"))
    assert job is not None
    assert job.submission_id == 17
    assert job.job_id == "job-17"
    assert job.queue_name == "jsg.v1:Ready_Grading"
    assert adapter._redis.claim_args == (
        "jsg.v1:Ready_Grading",
        "jsg.v1:Ready_Grading:processing",
        7,
    )


def test_redis_queue_adapter_dequeue_invalid_payload_removed() -> None:
    class _FakeRedis:
        def __init__(self) -> None:
            self.removed: tuple[str, int, str] | None = None

        async def brpoplpush(self, src: str, dst: str, timeout: int):
            return "not-json"

        async def lrem(self, queue_name: str, count: int, payload: str) -> None:
            self.removed = (queue_name, count, payload)

    adapter = object.__new__(queue_module.RedisQueueAdapter)
    adapter._redis = _FakeRedis()
    adapter._poll_timeout_s = 3

    job = _run(adapter.dequeue("queue"))
    assert job is None
    assert adapter._redis.removed == ("queue:processing", 1, "not-json")


def test_redis_queue_adapter_ack_and_fail_remove_processing_item() -> None:
    class _FakeRedis:
        def __init__(self) -> None:
            self.removed: list[tuple[str, int, str]] = []

        async def lrem(self, queue_name: str, count: int, payload: str) -> None:
            self.removed.append((queue_name, count, payload))

    adapter = object.__new__(queue_module.RedisQueueAdapter)
    adapter._redis = _FakeRedis()
    job = queue_module.QueueJob(
        submission_id=1,
        job_id="job-1",
        raw_payload='{"submission_id":1}',
        queue_name="queue",
    )

    _run(adapter.ack(job))
    _run(adapter.fail(job))

    assert adapter._redis.removed == [
        ("queue:processing", 1, '{"submission_id":1}'),
        ("queue:processing", 1, '{"submission_id":1}'),
    ]


def test_placeholder_database_adapter_raises() -> None:
    adapter = db_module.PlaceholderDatabaseAdapter(RuntimeError("nope"))
    with pytest.raises(RuntimeError):
        _run(adapter.get_transcription(1))


def test_create_database_adapter_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(db_module, "SQLAlchemyDatabaseAdapter", _boom)
    adapter = db_module.create_database_adapter(Path("."))
    assert isinstance(adapter, db_module.PlaceholderDatabaseAdapter)


class _FakeSelect:
    def __init__(self, model: object) -> None:
        self.model = model

    def where(self, *_args: object, **_kwargs: object) -> _FakeSelect:
        return self


class _FakeResult:
    def __init__(self, result: object | None) -> None:
        self._result = result

    def scalar_one_or_none(self) -> object | None:
        return self._result


class _FakeSession:
    def __init__(self, existing: object | None = None) -> None:
        self._existing = existing
        self.added: list[object] = []
        self.committed = False

    async def execute(self, _query: object) -> _FakeResult:
        return _FakeResult(self._existing)

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.committed = True


class _SessionContext:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeAIFeedback:
    submission_id = "submission_id"

    def __init__(
        self,
        submission_id: int,
        suggested_grade: float | None,
        instructor_guidance: str | None,
        student_feedback: str | None,
    ) -> None:
        self.submission_id = submission_id
        self.suggested_grade = suggested_grade
        self.instructor_guidance = instructor_guidance
        self.student_feedback = student_feedback


def _make_fake_adapter(session: _FakeSession) -> db_module.SQLAlchemyDatabaseAdapter:
    adapter = object.__new__(db_module.SQLAlchemyDatabaseAdapter)

    def _session_factory() -> _SessionContext:
        return _SessionContext(session)

    def _select(model: object) -> _FakeSelect:
        return _FakeSelect(model)

    adapter._async_session_factory = _session_factory
    adapter._select = _select
    adapter._AIFeedback = _FakeAIFeedback
    return adapter


def test_sqlalchemy_adapter_save_feedback_inserts() -> None:
    session = _FakeSession()
    adapter = _make_fake_adapter(session)
    payload = _build_valid_payload(submission_id=1)

    _run(adapter.save_feedback(1, payload))

    assert session.added
    saved = session.added[0]
    assert saved.suggested_grade == pytest.approx(float(payload["total_score"]))
    assert saved.student_feedback == payload["feedback"]["summary"]
    assert isinstance(saved.instructor_guidance, str)


def test_sqlalchemy_adapter_save_feedback_updates() -> None:
    existing = _FakeAIFeedback(
        submission_id=2,
        suggested_grade=None,
        instructor_guidance=None,
        student_feedback=None,
    )
    session = _FakeSession(existing=existing)
    adapter = _make_fake_adapter(session)
    payload = _build_valid_payload(submission_id=2, total_score=5.0)

    _run(adapter.save_feedback(2, payload))

    assert not session.added
    assert existing.suggested_grade == pytest.approx(5.0)
    assert existing.student_feedback == payload["feedback"]["summary"]
    assert isinstance(existing.instructor_guidance, str)


def test_sqlalchemy_adapter_persist_failure_feedback() -> None:
    session = _FakeSession()
    adapter = _make_fake_adapter(session)

    _run(adapter.persist_failure_feedback(3, "boom", "{bad json}"))

    assert session.added
    saved = session.added[0]
    assert saved.suggested_grade is None
    assert saved.student_feedback is None
    assert "ai_grading_failed" in (saved.instructor_guidance or "")


def test_sqlalchemy_adapter_get_sandbox_results_runtime_outputs() -> None:
    adapter = object.__new__(db_module.SQLAlchemyDatabaseAdapter)

    class _Compile:
        compiled_ok = True
        compile_errors = "ce"
        runtime_errors = "re"
        runtime_outputs = "out"

    class _Submission:
        compile_results = _Compile()

    async def _get_submission(_: int):
        await _async_noop()
        return _Submission()

    adapter._get_submission = _get_submission
    results = _run(adapter.get_sandbox_results(1))
    assert "runtime_output:" in results
    assert "out" in results


def test_sqlalchemy_adapter_get_sandbox_results_runtime_output_fallback() -> None:
    adapter = object.__new__(db_module.SQLAlchemyDatabaseAdapter)

    class _Compile:
        compiled_ok = True
        compile_errors = "ce"
        runtime_errors = "re"
        runtime_output = "legacy-out"

    class _Submission:
        compile_results = _Compile()

    async def _get_submission(_: int):
        await _async_noop()
        return _Submission()

    adapter._get_submission = _get_submission
    results = _run(adapter.get_sandbox_results(1))
    assert "legacy-out" in results


def test_run_worker_raises_on_placeholder_db(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeQueueAdapter:
        last_instance = None

        def __init__(self, redis_url: str, poll_timeout_s: int = 5):
            self.closed = False
            _FakeQueueAdapter.last_instance = self

        async def dequeue(self, queue_name: str):
            return None

        async def push(self, queue_name: str, payload: str) -> None:
            return None

        async def ack(self, job: queue_module.QueueJob) -> None:
            return None

        async def fail(self, job: queue_module.QueueJob) -> None:
            return None

        async def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(grader_main, "RedisQueueAdapter", _FakeQueueAdapter)
    placeholder = grader_main.PlaceholderDatabaseAdapter(RuntimeError("boom"))
    monkeypatch.setattr(grader_main, "create_database_adapter", lambda _: placeholder)

    with pytest.raises(RuntimeError):
        _run(grader_main.run_worker(settings=_make_settings(), once=True))


# Additional comprehensive tests for missing coverage


def test_parser_rejects_wrong_data_types() -> None:
    """Test parser rejects invalid data types in required fields."""
    # Wrong type for submission_id (should be int)
    payload = _build_valid_payload()
    payload["submission_id"] = "not-an-int"
    with pytest.raises(JSONValidationError):
        parse_and_validate_json(json.dumps(payload))

    # Wrong type for total_score (should be number)
    payload = _build_valid_payload()
    payload["total_score"] = "not-a-number"
    with pytest.raises(JSONValidationError):
        parse_and_validate_json(json.dumps(payload))

    # Wrong type for confidence (should be number)
    payload = _build_valid_payload()
    payload["confidence"] = "not-a-number"
    with pytest.raises(JSONValidationError):
        parse_and_validate_json(json.dumps(payload))


def test_parser_rejects_boundary_values() -> None:
    """Test parser rejects invalid boundary values."""
    # Negative total_score
    payload = _build_valid_payload(total_score=-1.0)
    with pytest.raises(JSONValidationError):
        parse_and_validate_json(json.dumps(payload))

    # total_score > max_score
    payload = _build_valid_payload(total_score=15.0, max_score=10.0)
    with pytest.raises(JSONValidationError):
        parse_and_validate_json(json.dumps(payload))

    # Invalid confidence range (< 0)
    payload = _build_valid_payload()
    payload["confidence"] = -0.1
    with pytest.raises(JSONValidationError):
        parse_and_validate_json(json.dumps(payload))

    # Invalid confidence range (> 1)
    payload = _build_valid_payload()
    payload["confidence"] = 1.5
    with pytest.raises(JSONValidationError):
        parse_and_validate_json(json.dumps(payload))


def test_parser_rejects_missing_required_fields() -> None:
    """Test parser rejects payloads missing required fields."""
    payload = _build_valid_payload()

    # Missing submission_id
    del payload["submission_id"]
    with pytest.raises(JSONValidationError):
        parse_and_validate_json(json.dumps(payload))

    # Missing total_score
    payload = _build_valid_payload()
    del payload["total_score"]
    with pytest.raises(JSONValidationError):
        parse_and_validate_json(json.dumps(payload))

    # Missing rubric_breakdown
    payload = _build_valid_payload()
    del payload["rubric_breakdown"]
    with pytest.raises(JSONValidationError):
        parse_and_validate_json(json.dumps(payload))


def test_parser_rejects_invalid_rubric_breakdown() -> None:
    """Test parser rejects invalid rubric breakdown structures."""
    payload = _build_valid_payload()

    # Invalid rubric item (missing required fields)
    payload["rubric_breakdown"] = [{"invalid": "item"}]
    with pytest.raises(JSONValidationError):
        parse_and_validate_json(json.dumps(payload))

    # Invalid rubric item (wrong types)
    payload["rubric_breakdown"] = [
        {
            "criterion_id_or_name": 123,  # Should be string
            "earned_points": "not-a-number",  # Should be number
            "max_points": 5,
            "rationale": "test",
            "evidence_from_code_or_logs": "test",
        }
    ]
    with pytest.raises(JSONValidationError):
        parse_and_validate_json(json.dumps(payload))

    # Negative earned_points
    payload["rubric_breakdown"] = [
        {
            "criterion_id_or_name": "Test",
            "earned_points": -1,
            "max_points": 5,
            "rationale": "test",
            "evidence_from_code_or_logs": "test",
        }
    ]
    with pytest.raises(JSONValidationError):
        parse_and_validate_json(json.dumps(payload))


def test_parser_rejects_invalid_feedback_structure() -> None:
    """Test parser rejects invalid feedback structures."""
    payload = _build_valid_payload()

    # Missing summary
    del payload["feedback"]["summary"]
    with pytest.raises(JSONValidationError):
        parse_and_validate_json(json.dumps(payload))

    # Invalid issues structure
    payload = _build_valid_payload()
    payload["feedback"]["issues"] = [{"invalid": "structure"}]
    with pytest.raises(JSONValidationError):
        parse_and_validate_json(json.dumps(payload))


def test_parser_rejects_invalid_error_classification() -> None:
    """Test parser rejects invalid error classification."""
    payload = _build_valid_payload()

    # Wrong type for boolean fields
    payload["error_classification"]["syntax_or_compile"] = "not-boolean"
    with pytest.raises(JSONValidationError):
        parse_and_validate_json(json.dumps(payload))


def test_validate_submission_id_mismatch() -> None:
    """Test submission ID validation catches mismatches."""
    payload = _build_valid_payload(submission_id=123)
    parsed = parse_and_validate_json(json.dumps(payload))

    # Mismatch should raise error
    with pytest.raises(JSONValidationError):
        validate_submission_id(parsed, 999)


def test_prompt_builder_edge_cases() -> None:
    """Test prompt builder handles edge cases."""
    schema = grading_schema()

    # Empty code
    prompt = construct_prompt(
        submission_id=1,
        code="",
        logs="test",
        rubric={"criteria": []},
        schema=schema,
    )
    assert "submission_id: 1" in prompt

    # Empty logs
    prompt = construct_prompt(
        submission_id=1,
        code="test",
        logs="",
        rubric={"criteria": []},
        schema=schema,
    )
    assert "Sandbox compile/run logs (verbatim):" in prompt

    # Empty rubric
    prompt = construct_prompt(
        submission_id=1,
        code="test",
        logs="test",
        rubric={},
        schema=schema,
    )
    assert "Rubric criteria and points (verbatim):" in prompt


def test_prompt_builder_special_characters() -> None:
    """Test prompt builder handles special characters properly."""
    schema = grading_schema()

    # Code with special characters
    code_with_special = (
        "class Main { public static void main(String[] args) { "
        'System.out.println("Hello\\nWorld"); } }'
    )
    prompt = construct_prompt(
        submission_id=1,
        code=code_with_special,
        logs="compiled_ok: true",
        rubric={"criteria": [{"name": "Test", "points": 10}]},
        schema=schema,
    )
    assert code_with_special in prompt


def test_prompt_builder_large_inputs() -> None:
    """Test prompt builder handles large inputs."""
    schema = grading_schema()

    # Large code
    large_code = "class Main {\n" + "    // Comment\n" * 1000 + "}"
    prompt = construct_prompt(
        submission_id=1,
        code=large_code,
        logs="compiled_ok: true",
        rubric={"criteria": [{"name": "Test", "points": 10}]},
        schema=schema,
    )
    assert len(prompt) > 1000  # Should handle large inputs


def test_llm_client_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test LLM client handles timeouts."""

    def handler(_: httpx.Request) -> httpx.Response:
        # Simulate timeout by not responding
        raise httpx.TimeoutException("timeout")

    transport = httpx.MockTransport(handler)
    _patch_async_client(monkeypatch, transport)

    client = LLMClient(_make_settings(max_retries=0))
    with pytest.raises(LLMAPIError):
        _run(client.call("prompt", submission_id=1))


def test_llm_client_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test LLM client handles empty responses."""

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    transport = httpx.MockTransport(handler)
    _patch_async_client(monkeypatch, transport)

    client = LLMClient(_make_settings())
    with pytest.raises(LLMAPIError):
        _run(client.call("prompt", submission_id=1))


def test_llm_client_malformed_content(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test LLM client handles malformed content in response."""

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": None}}]},
        )

    transport = httpx.MockTransport(handler)
    _patch_async_client(monkeypatch, transport)

    client = LLMClient(_make_settings())
    with pytest.raises(LLMAPIError):
        _run(client.call("prompt", submission_id=1))


def test_grading_schema_structure() -> None:
    """Test that grading schema has expected structure."""
    schema = grading_schema()

    assert isinstance(schema, dict)
    assert "$defs" in schema
    assert "type" in schema
    assert schema["type"] == "object"
    assert "properties" in schema
    assert "required" in schema

    # Check required fields are present
    required_fields = [
        "submission_id",
        "total_score",
        "max_score",
        "rubric_breakdown",
        "feedback",
        "error_classification",
        "confidence",
    ]
    for field in required_fields:
        assert field in schema["properties"]
        assert field in schema["required"]


def test_parse_with_single_repair_max_retries() -> None:
    """Test that repair logic doesn't retry more than once."""
    llm_client = _DummyLLMClient(outputs=["bad-json", "still-bad"])
    with pytest.raises(JSONValidationError):
        _run(
            grader_main._parse_with_single_repair(
                submission_id=1,
                first_response_text="not-json",
                llm_client=llm_client,
            )
        )
    # Should have made exactly one repair call
    assert len(llm_client.calls) == 1


def test_process_submission_invalid_payload_inputs() -> None:
    """Test process_submission handles invalid payload inputs."""
    db_adapter = _DummyDBAdapter()
    # Set up db_adapter to return empty/invalid data
    db_adapter.transcription = ""
    db_adapter.logs = ""
    db_adapter.rubric = {}
    llm_client = _DummyLLMClient(outputs=[_valid_json(submission_id=1)])
    settings = _make_settings()

    # Empty payload_inputs should fall back to DB, which has empty data
    result = _run(
        grader_main.process_submission(
            submission_id=1,
            db_adapter=db_adapter,
            llm_client=llm_client,
            settings=settings,
            payload_inputs={},  # Empty - should use DB
        )
    )
    # Should still work with empty data from DB
    assert result["status"] == "COMPLETED"


def test_format_sandbox_logs_edge_cases() -> None:
    """Test sandbox log formatting with edge cases."""
    # Empty result
    formatted = grader_main._format_sandbox_logs({})
    assert formatted == ""

    # Missing keys
    result = {"result": {}}
    formatted = grader_main._format_sandbox_logs(result)
    assert "compiled_ok: None" in formatted
    assert "compile_errors:" in formatted

    # Invalid types
    result = {"result": {"compilation_result": {"success": "not-bool"}}}
    formatted = grader_main._format_sandbox_logs(result)
    assert "compiled_ok: not-bool" in formatted


def test_payload_inputs_from_raw_edge_cases() -> None:
    """Test payload parsing from raw JSON with edge cases."""
    # Invalid JSON
    assert grader_main._payload_inputs_from_raw("invalid") is None

    # Valid but incomplete
    payload = {"transcribed_text": "code"}
    parsed = grader_main._payload_inputs_from_raw(json.dumps(payload))
    assert parsed is not None
    assert parsed["code"] == "code"
    assert parsed["rubric"] == {}
    assert parsed["logs"] == ""

    # Valid complete
    payload = {
        "transcribed_text": "code",
        "rubric_json": {"criteria": []},
        "sandbox_result": {"result": {"compilation_result": {"success": True}}},
    }
    parsed = grader_main._payload_inputs_from_raw(json.dumps(payload))
    assert parsed is not None
    assert parsed["code"] == "code"
    assert parsed["rubric"] == {"criteria": []}
    assert "compiled_ok: True" in parsed["logs"]


def test_extract_submission_id_edge_cases() -> None:
    """Test submission ID extraction with edge cases."""
    # Empty string
    with pytest.raises(ValueError):
        queue_module.RedisQueueAdapter._extract_submission_id("")

    # Nested but invalid (string instead of int)
    with pytest.raises(ValueError):
        queue_module.RedisQueueAdapter._extract_submission_id(
            json.dumps({"deep": {"nested": {"id": "not-int"}}})
        )

    # Valid nested - but the function doesn't support this path
    with pytest.raises(ValueError):
        queue_module.RedisQueueAdapter._extract_submission_id(
            json.dumps({"data": {"submission_id": 42}})
        )


def test_extract_job_id_edge_cases() -> None:
    """Test job ID extraction with edge cases."""
    # Valid cases
    assert (
        queue_module.RedisQueueAdapter._extract_job_id(json.dumps({"job_id": 123}))
        == "123"
    )
    assert (
        queue_module.RedisQueueAdapter._extract_job_id(json.dumps({"job_id": "abc"}))
        == "abc"
    )

    # Invalid cases
    assert (
        queue_module.RedisQueueAdapter._extract_job_id(json.dumps({"no_job_id": 1}))
        is None
    )
    assert queue_module.RedisQueueAdapter._extract_job_id("not-json") is None


def test_build_completion_payload_edge_cases() -> None:
    """Test completion payload building with edge cases."""
    job = queue_module.QueueJob(
        submission_id=1,
        job_id="job-1",
        raw_payload="{}",
        queue_name="queue",
    )

    # Missing parsed_feedback
    outcome = {"status": "COMPLETED"}
    payload = grader_main._build_completion_payload(job=job, outcome=outcome)
    assert "final_grade" not in payload
    assert payload["rubric_result_json"] == {}

    # Invalid parsed_feedback
    outcome = {"status": "COMPLETED", "parsed_feedback": {}}
    payload = grader_main._build_completion_payload(job=job, outcome=outcome)
    assert "final_grade" not in payload
    assert payload["rubric_result_json"] == {}


def test_live_llm_call() -> None:
    api_key = os.getenv("API_KEY", "")
    model = os.getenv("MODEL", "")
    if not api_key or not model:
        pytest.skip("Skipping live LLM test: API_KEY or MODEL not set.")

    settings = load_settings()
    client = LLMClient(settings)

    schema = grading_schema()
    prompt = construct_prompt(
        submission_id=1,
        code="class Main { public static void main(String[] args) { "
        "System.out.println(1 + 1); } }",
        logs="compiled_ok: true\nruntime_output:\n2",
        rubric={"criteria": [{"name": "Correctness", "points": 10}]},
        schema=schema,
    )

    response = _run(client.call(prompt, submission_id=1))
    parsed = parse_and_validate_json(response.text)
    validate_submission_id(parsed, 1)
    assert float(parsed["total_score"]) <= float(parsed["max_score"])


def test_run_worker_once_processes_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeQueueAdapter:
        last_instance = None

        def __init__(self, redis_url: str, poll_timeout_s: int = 5):
            self.pushed: list[tuple[str, str]] = []
            self.acked: list[queue_module.QueueJob] = []
            self.failed: list[queue_module.QueueJob] = []
            self.dequeued = False
            self.closed = False
            self.last_queue = None
            _FakeQueueAdapter.last_instance = self

        async def dequeue(self, queue_name: str):
            self.last_queue = queue_name
            if self.dequeued:
                return None
            self.dequeued = True
            return queue_module.QueueJob(
                submission_id=21,
                job_id="job-21",
                raw_payload="{}",
                queue_name=queue_name,
            )

        async def push(self, queue_name: str, payload: str) -> None:
            self.pushed.append((queue_name, payload))

        async def ack(self, job: queue_module.QueueJob) -> None:
            self.acked.append(job)

        async def fail(self, job: queue_module.QueueJob) -> None:
            self.failed.append(job)

        async def close(self) -> None:
            self.closed = True

    async def _fake_process_submission(**kwargs: object) -> dict:
        await _async_noop()
        return {
            "status": "COMPLETED",
            "parsed_feedback": {
                "total_score": 4,
                "feedback": {"summary": "ok"},
            },
        }

    monkeypatch.setattr(grader_main, "RedisQueueAdapter", _FakeQueueAdapter)
    monkeypatch.setattr(grader_main, "create_database_adapter", lambda _: object())
    monkeypatch.setattr(grader_main, "process_submission", _fake_process_submission)

    settings = _make_settings()
    _run(grader_main.run_worker(settings=settings, once=True))

    adapter = _FakeQueueAdapter.last_instance
    assert adapter.closed is True
    assert adapter.pushed
    queue_name, payload = adapter.pushed[0]
    assert queue_name == f"{settings.ready_queue_name}:completed:job-21"
    payload_json = json.loads(payload)
    assert payload_json["submission_id"] == 21
    assert payload_json["status"] == "COMPLETED"
    assert len(adapter.acked) == 1
    assert not adapter.failed
