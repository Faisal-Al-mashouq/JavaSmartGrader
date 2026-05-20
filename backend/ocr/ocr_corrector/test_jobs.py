"""
Push sample OCR jobs to Redis for testing.

Usage (from backend/):
    python -m ocr_corrector.test_jobs
"""

import json
import logging
import uuid

import redis
from settings import settings

logger = logging.getLogger(__name__)
OCR_QUEUE = f"{settings.queue_namespace}:{settings.ocr_queue}"

if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    logger.info("Pushing test OCR jobs to %s...", OCR_QUEUE)

    r = redis.Redis.from_url(
        settings.redis_endpoint,
        decode_responses=True,
    )

    # Test job 1: Simple image path
    payload1 = json.dumps(
        {
            "job_id": str(uuid.uuid4()),
            "image_path": "/uploads/exam_001.jpg",
            "submission_id": str(uuid.uuid4()),
            "transcription_id": 1,
        }
    )
    r.lpush(OCR_QUEUE, payload1)
    logger.info("Test job 1 pushed to %s", OCR_QUEUE)

    # Test job 2: Another submission
    payload2 = json.dumps(
        {
            "job_id": str(uuid.uuid4()),
            "image_path": "/uploads/exam_002.png",
            "submission_id": str(uuid.uuid4()),
            "transcription_id": 2,
        }
    )
    r.lpush(OCR_QUEUE, payload2)
    logger.info("Test job 2 pushed to %s", OCR_QUEUE)

    # Test job 3: No submission_id (standalone OCR)
    payload3 = json.dumps(
        {
            "job_id": str(uuid.uuid4()),
            "image_path": "/uploads/exam_003.jpg",
            "submission_id": None,
            "transcription_id": None,
        }
    )
    r.lpush(OCR_QUEUE, payload3)
    logger.info("Test job 3 pushed to %s", OCR_QUEUE)

    logger.info("All test jobs pushed. Start the worker with:")
    logger.info("  python -m ocr_corrector.ocr_worker")
