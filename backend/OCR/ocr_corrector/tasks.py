"""
Redis job queue integration.

Provides helpers to enqueue image correction jobs and a worker
loop that processes them. Uses Redis lists for a simple FIFO queue
and stores results as JSON with a configurable TTL.

Queue design::

    ocr:jobs        → Redis list (FIFO)
    ocr:result:<id> → JSON hash with CorrectionResult.to_dict()
    ocr:status:<id> → pending | processing | completed | failed

Usage
-----
Enqueue a job (from your API / web server)::

    from ocr_corrector.tasks import enqueue_job
    job_id = enqueue_job("/uploads/exam_001.jpg")

Run the worker (from CLI or supervisor)::

    python -m ocr_corrector.tasks
"""

from __future__ import annotations

import json
import uuid
import logging
import time

import redis

from ocr_corrector.config import REDIS_URL, REDIS_QUEUE_NAME, REDIS_RESULT_TTL
from ocr_corrector.pipeline import OCRCorrectionPipeline

logger = logging.getLogger(__name__)


def _get_redis() -> redis.Redis:
    return redis.from_url(REDIS_URL, decode_responses=True)


# ── Enqueue ──────────────────────────────────────────────────────

def enqueue_job(image_path: str, model: str | None = None) -> str:
    """
    Push a correction job onto the Redis queue.

    Parameters
    ----------
    image_path : str
        Path to the image file the worker can access.
    model : str, optional
        Override the default Gemini model.

    Returns
    -------
    str
        A unique job ID to poll for results.
    """
    r = _get_redis()
    job_id = uuid.uuid4().hex[:12]

    payload = json.dumps({
        "job_id": job_id,
        "image_path": image_path,
        "model": model,
    })

    r.set(f"ocr:status:{job_id}", "pending", ex=REDIS_RESULT_TTL)
    r.lpush(REDIS_QUEUE_NAME, payload)

    logger.info("Enqueued job %s for '%s'.", job_id, image_path)
    return job_id


# ── Query ────────────────────────────────────────────────────────

def get_job_status(job_id: str) -> str | None:
    """Return the current status of a job, or None if not found."""
    return _get_redis().get(f"ocr:status:{job_id}")


def get_job_result(job_id: str) -> dict | None:
    """Return the full result dict, or None if not ready."""
    raw = _get_redis().get(f"ocr:result:{job_id}")
    return json.loads(raw) if raw else None


# ── Worker ───────────────────────────────────────────────────────

def process_one(r: redis.Redis, pipeline: OCRCorrectionPipeline) -> bool:
    """
    Block-pop one job from the queue and process it.

    Returns True if a job was processed, False on timeout.
    """
    item = r.brpop(REDIS_QUEUE_NAME, timeout=5)
    if item is None:
        return False

    _, raw_payload = item
    job = json.loads(raw_payload)
    job_id = job["job_id"]

    logger.info("Processing job %s ...", job_id)
    r.set(f"ocr:status:{job_id}", "processing", ex=REDIS_RESULT_TTL)

    result = pipeline.run(
        image_path=job["image_path"],
    )

    r.set(f"ocr:result:{job_id}", json.dumps(result.to_dict()), ex=REDIS_RESULT_TTL)
    r.set(f"ocr:status:{job_id}", result.status, ex=REDIS_RESULT_TTL)

    logger.info("Job %s → %s", job_id, result.status)
    return True


def run_worker() -> None:
    """
    Start an infinite worker loop that processes jobs from Redis.

    Designed to be run as a long-lived process (e.g., via systemd,
    Docker, or ``python -m ocr_corrector.tasks``).
    """
    logger.info("Worker started. Listening on '%s'...", REDIS_QUEUE_NAME)

    r = _get_redis()
    pipeline = OCRCorrectionPipeline()

    try:
        while True:
            try:
                process_one(r, pipeline)
            except redis.ConnectionError:
                logger.warning("Redis connection lost. Retrying in 5s...")
                time.sleep(5)
            except Exception:
                logger.exception("Error processing job. Continuing...")
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Worker stopped.")


# Allow running the worker directly: python -m ocr_corrector.tasks
if __name__ == "__main__":
    run_worker()
