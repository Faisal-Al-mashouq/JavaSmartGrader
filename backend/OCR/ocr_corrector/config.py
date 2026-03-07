"""
Configuration and environment variable management.

Loads API keys and service endpoints from ``.env`` and exposes
them as module-level constants. Call ``validate()`` at startup
to fail fast on missing credentials.
"""

import logging

from logs import setup_logging
from settings import settings

setup_logging()

# ── Logging ──────────────────────────────────────────────────────
LOG_LEVEL = logging.getLogger(__name__)

# ── Azure Document Intelligence ──────────────────────────────────
AZURE_ENDPOINT = settings.azure_ocr_endpoint
AZURE_KEY = settings.api_azure

# ── Gemini (Google GenAI) ────────────────────────────────────────
GEMINI_KEY = settings.api_gemini
GEMINI_MODEL = settings.gemini_model

# ── Redis (for job queue integration) ────────────────────────────
REDIS_URL = settings.redis_endpoint
REDIS_QUEUE_NAME = "ocr:jobs"
REDIS_RESULT_TTL = 3600  # seconds


def validate() -> None:
    """Raise ``EnvironmentError`` if any required API key is missing."""
    required = {
        "API_AZURE": AZURE_KEY,
        "API_GEMINI": GEMINI_KEY,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise OSError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Copy .env.template → .env and fill in your keys."
        )
