from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime

from core.job_queue import (
    MAIN_QUEUE,
    initialize_job,
    return_result,
    set_result,
)
from schemas import Job, JobRequest, JobStatus
from schemas.shared import TestCase as SchemaTestCase


def _run(coro):
    return asyncio.run(coro)


def _sample_job_request() -> JobRequest:
    return JobRequest(
        submission_id=1,
        question_id=2,
        assignment_id=3,
        student_id=4,
        image_url="page.png",
        java_code="public class Main {}",
        test_cases=[SchemaTestCase(input=" ", expected_output="Hello")],
        rubric_json={"criteria": {"Correctness": {"weight": 100}}},
    )


def test_initialize_job_parses_valid_json() -> None:
    req = _sample_job_request()
    raw = req.model_dump_json()
    job = _run(initialize_job(raw))
    assert job is not None
    assert job.status == JobStatus.PENDING
    assert job.initial_request.submission_id == req.submission_id
    assert job.finished_at is None


def test_initialize_job_returns_none_on_invalid_json() -> None:
    assert _run(initialize_job("not-json")) is None


def test_initialize_job_returns_none_on_schema_mismatch() -> None:
    raw = json.dumps({"submission_id": "x"})
    assert _run(initialize_job(raw)) is None


def test_set_result_updates_status_and_finished_at() -> None:
    req = _sample_job_request()
    job = Job(
        job_id=uuid.uuid4(),
        status=JobStatus.PENDING,
        initial_request=req,
        created_at=datetime.now(UTC),
        finished_at=None,
    )
    out = _run(set_result(job, JobStatus.COMPLETED))
    assert out.status == JobStatus.COMPLETED
    assert out.finished_at is not None


def test_return_result_pushes_to_completed_queue() -> None:
    pushed: list[tuple[str, str]] = []

    class _FakeRedis:
        async def lpush(self, queue_name: str, payload: str) -> None:
            pushed.append((queue_name, payload))

    class _FakeClient:
        redis_client = _FakeRedis()

    req = _sample_job_request()
    job = Job(
        job_id=uuid.uuid4(),
        status=JobStatus.COMPLETED,
        initial_request=req,
        created_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
    )

    async def _go() -> bool:
        return await return_result(_FakeClient(), job)

    ok = _run(_go())
    assert ok is True
    assert len(pushed) == 1
    assert pushed[0][0] == f"{MAIN_QUEUE}:completed"
    assert str(job.job_id) in pushed[0][1]
