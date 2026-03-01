"""
Configuration and environment variable management.

Loads API keys and service endpoints from ``.env`` and exposes
them as module-level constants. Call ``validate()`` at startup
to fail fast on missing credentials.
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

# ── Logging ──────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s │ %(name)-18s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)

# ── Azure Document Intelligence ──────────────────────────────────
AZURE_ENDPOINT = os.getenv(
    "AZURE_ENDPOINT",
    "https://gpfirsttrydoc.cognitiveservices.azure.com/",
)
AZURE_KEY = os.getenv("API_AZURE")

# ── Gemini (Google GenAI) ────────────────────────────────────────
GEMINI_KEY = os.getenv("API_GEMINI")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-preview")

# ── Redis (for job queue integration) ────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_QUEUE_NAME = os.getenv("REDIS_QUEUE_NAME", "ocr:jobs")
REDIS_RESULT_TTL = int(os.getenv("REDIS_RESULT_TTL", "3600"))  # seconds


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
