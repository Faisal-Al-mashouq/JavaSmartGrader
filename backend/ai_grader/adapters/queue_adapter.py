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
    an immutable object containing the ID, the raw message, and the source queue name
    """
    submission_id: int
    raw_payload: str
    queue_name: str


class QueueAdapter(Protocol):
    """
    defines the mandatory blueprint for any queue implementation (like Redis)
    ensures any subclass provides a standard dequeue method
    how: Uses Python's protocol to support structural typing 
    """
    async def dequeue(self, queue_name: str) -> QueueJob | None:
        """Pop one job from queue_name."""


class RedisQueueAdapter:
    """
    handles the actual communication with a Redis server to fetch and parse jobs
    output: a QueueJob object or None if the queue is empty
    uses brpop for non-blocking asynchronous polling and includes logic to extract IDs from various JSON formats
    """
    def __init__(self, redis_url: str, poll_timeout_s: int = 5):
        redis_module = importlib.import_module("redis.asyncio")
        self._redis = redis_module.Redis.from_url(redis_url, decode_responses=True)
        self._poll_timeout_s = poll_timeout_s

    async def dequeue(self, queue_name: str) -> QueueJob | None:
        item = await self._redis.brpop(queue_name, timeout=self._poll_timeout_s)
        if item is None:
            return None

        queue_name_from_redis, raw_payload = item
        try:
            submission_id = self._extract_submission_id(raw_payload)
        except ValueError as exc:
            logger.error(
                "Skipping queue payload with missing submission_id on queue=%s: %s",
                queue_name_from_redis,
                exc,
            )
            return None

        return QueueJob(
            submission_id=submission_id,
            raw_payload=raw_payload,
            queue_name=queue_name_from_redis,
        )

    async def close(self) -> None:
        await self._redis.aclose()

    @staticmethod
    def _extract_submission_id(raw_payload: str) -> int:
        """
        a defensive helper that hunts for an ID inside potentially messy or nested JSON payloads
        output: a clean integer submission_id
        how: systematically checks for direct integers, top-level keys (id, submission_id), or nested fields
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
