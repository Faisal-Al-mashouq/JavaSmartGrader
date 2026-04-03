import logging

from redis.asyncio import Redis
from settings import settings

logger = logging.getLogger(__name__)


class JobQueue:
    def __init__(
        self,
        redis_url: str = settings.redis_endpoint,
        ai_grading_max_concurrency: int = settings.ai_grading_max_concurrency,
    ):
        self.redis_url: str = redis_url
        self.ai_grading_max_concurrency: int = ai_grading_max_concurrency
        self.redis_client = Redis.from_url(self.redis_url, decode_responses=True)
