from __future__ import annotations

import importlib
import json
import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QueueJob:
    """
    An immutable object containing the ID, optional job id, the raw message,
    and the source queue name.
    """

    submission_id: int
    job_id: str | None
    raw_payload: str
    queue_name: str


class QueueAdapter(Protocol):
    """
    defines the mandatory blueprint for any queue implementation (like Redis)
    ensures any subclass provides a standard claim/push/ack/fail workflow
    how: Uses Python's protocol to support structural typing
    """

    async def dequeue(self, queue_name: str) -> QueueJob | None:
        """Atomically claim one job from queue_name."""

    async def push(self, queue_name: str, payload: str) -> None:
        """Push a payload onto a queue."""

    async def ack(self, job: QueueJob) -> None:
        """Remove a completed/handled job from the processing queue."""

    async def fail(self, job: QueueJob) -> None:
        """Remove a failed job from the processing queue."""


class RedisQueueAdapter:
    """
    handles the actual communication with a Redis server to fetch and parse jobs
    output: a QueueJob object or None if the queue is empty
    uses BRPOPLPUSH for atomic claim into a :processing queue and includes
    logic to extract IDs from various JSON formats
    """

    def __init__(self, redis_url: str, poll_timeout_s: int = 5):
        redis_module = importlib.import_module("redis.asyncio")
        self._redis = redis_module.Redis.from_url(redis_url, decode_responses=True)
        self._poll_timeout_s = poll_timeout_s

    @staticmethod
    def _processing_queue_name(queue_name: str) -> str:
        return f"{queue_name}:processing"

    async def dequeue(self, queue_name: str) -> QueueJob | None:
        processing_queue = self._processing_queue_name(queue_name)
        raw_payload = await self._redis.brpoplpush(
            src=queue_name,
            dst=processing_queue,
            timeout=self._poll_timeout_s,
        )
        if raw_payload is None:
            return None

        try:
            submission_id = self._extract_submission_id(raw_payload)
        except ValueError as exc:
            logger.error(
                "Skipping queue payload with missing submission_id on queue=%s: %s",
                queue_name,
                exc,
            )
            await self._redis.lrem(processing_queue, 1, raw_payload)
            return None

        job_id = self._extract_job_id(raw_payload)
        return QueueJob(
            submission_id=submission_id,
            job_id=job_id,
            raw_payload=raw_payload,
            queue_name=queue_name,
        )

    async def push(self, queue_name: str, payload: str) -> None:
        await self._redis.lpush(queue_name, payload)

    async def ack(self, job: QueueJob) -> None:
        processing_queue = self._processing_queue_name(job.queue_name)
        await self._redis.lrem(processing_queue, 1, job.raw_payload)

    async def fail(self, job: QueueJob) -> None:
        processing_queue = self._processing_queue_name(job.queue_name)
        await self._redis.lrem(processing_queue, 1, job.raw_payload)

    async def close(self) -> None:
        await self._redis.aclose()

    @staticmethod
    def _extract_submission_id(raw_payload: str) -> int:
        """
        a defensive helper that hunts for an ID inside potentially messy or
        nested JSON payloads
        output: a clean integer submission_id
        how: systematically checks for direct integers, top-level keys (id,
        submission_id), or nested fields
        """
        stripped = raw_payload.strip()
        if stripped.isdigit():
            return int(stripped)

        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Payload is not JSON or integer: {raw_payload!r}"
            ) from exc

        if isinstance(payload, int):
            return payload
        if isinstance(payload, str) and payload.isdigit():
            return int(payload)
        if not isinstance(payload, dict):
            raise ValueError("JSON payload must be object/int/string")

        for key in ("submission_id", "id"):
            value = payload.get(key)
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)

        submission = payload.get("submission")
        if isinstance(submission, dict):
            nested_value = submission.get("id")
            if isinstance(nested_value, int):
                return nested_value
            if isinstance(nested_value, str) and nested_value.isdigit():
                return int(nested_value)

        raise ValueError("Could not extract submission_id from payload")

    @staticmethod
    def _extract_job_id(raw_payload: str) -> str | None:
        stripped = raw_payload.strip()
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            return None

        if isinstance(payload, dict):
            job_id = payload.get("job_id")
            if job_id is None:
                return None
            return str(job_id)
        return None
