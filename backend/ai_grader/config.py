from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env once so local development values are available before reading
# os.getenv(...) in load_settings().
load_dotenv()

# Centralises all runtime configuration
# Settings are loaded once at startup from environment variables
# All values are validated at load time so misconfiguration is caught
# immediately rather than at first use


def _read_int(name: str, default: int, minimum: int | None = None) -> int:
    """
    Reads an integer env var and raises ValueError if the value cannot be cast
    or falls below min
    Returns: int
    """
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer. Got: {raw!r}") from exc
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}. Got: {value}")
    return value


def _read_float(name: str, default: float, minimum: float | None = None) -> float:
    """
    Reads a float env var with the same validation logic as _read_int.
    Returns: float
    """
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number. Got: {raw!r}") from exc
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}. Got: {value}")
    return value


def _read_csv(name: str, default: str) -> tuple[str, ...]:
    """
    Reads a comma-separated env var and returns a tuple of non-empty stripped strings.
    Returns: tuple[str, ...]
    """
    raw = os.getenv(name, default)
    values = [item.strip() for item in raw.split(",")]
    return tuple(item for item in values if item)


@dataclass(frozen=True)
class Settings:
    """
    model: Fine-tuned model ID
    api_key: API key
    base_url: OpenAI-compatible base URL
    timeout_s: HTTP request timeout
    max_retries: Number of additional attempts after failure
    backoff_base_s: Starting delay for exponential backoff
    backoff_max_s: Cap on backoff delay (adds jitter)
    redis_url: Redis connection URL
    ready_queue_name: Redis list name for worker pops.
    queue_poll_timeout_s: BRPOP blocking timeout in seconds
    temperature: LLM sampling temperature
    pending_review_status: Status applied after successful grading.
    failure_status_candidates: Ordered list of status strings for failures
    backend_path: Filesystem path added to sys.path for DB imports
    """

    model: str
    api_key: str
    base_url: str
    timeout_s: float
    max_retries: int
    backoff_base_s: float
    backoff_max_s: float
    redis_url: str
    ready_queue_name: str
    queue_poll_timeout_s: int
    temperature: float
    pending_review_status: str
    failure_status_candidates: tuple[str, ...]
    backend_path: Path


def load_settings() -> Settings:
    """
    Constructs and returns the single Settings instance. Called once in main()
    and passed to all components.
    Returns: Settings (frozen dataclass)
    """
    repo_root = Path(__file__).resolve().parents[1]
    # BACKEND_PATH is where `db.*` modules live (for dynamic adapter imports).
    # Override this in .env when running outside the expected project layout.
    backend_path = Path(os.getenv("BACKEND_PATH", str(repo_root / "backend")))

    # Queue names are namespace-aware so multiple environments can share one
    # Redis instance safely.
    queue_namespace = os.getenv("QUEUE_NAMESPACE", "jsg.v1")
    ready_queue_base = os.getenv("READY_GRADING_QUEUE", "Ready_Grading")
    if queue_namespace:
        prefix = f"{queue_namespace}:"
        ready_queue_name = (
            ready_queue_base
            if ready_queue_base.startswith(prefix)
            else f"{prefix}{ready_queue_base}"
        )
    else:
        ready_queue_name = ready_queue_base

    return Settings(
        # LLM endpoint configuration.
        model=os.getenv("MODEL", "ft:gpt-4.1-nano-"),
        api_key=os.getenv("API_KEY", ""),
        base_url=os.getenv("BASE_URL", "https://api.openai.com/v1"),
        timeout_s=_read_float("TIMEOUT_S", 30.0, minimum=1.0),
        max_retries=_read_int("MAX_RETRIES", 3, minimum=0),
        backoff_base_s=_read_float("BACKOFF_BASE_S", 1.0, minimum=0.0),
        backoff_max_s=_read_float("BACKOFF_MAX_S", 30.0, minimum=0.1),
        # Redis URL priority: REDIS_ENDPOINT > REDIS_URL > hardcoded default.
        redis_url=os.getenv(
            "REDIS_ENDPOINT",
            os.getenv("REDIS_URL", "redis://redis:6379"),
        ),
        ready_queue_name=ready_queue_name,
        queue_poll_timeout_s=_read_int("QUEUE_POLL_TIMEOUT_S", 5, minimum=0),
        # Submission state transitions after success/failure.
        pending_review_status=os.getenv("PENDING_REVIEW_STATUS", "Pending_Review"),
        failure_status_candidates=_read_csv(
            "FAILURE_STATUS_CANDIDATES",
            "Grading_Failed,failed",
        ),
        temperature=_read_float("LLM_TEMPERATURE", 0.0, minimum=0.0),
        backend_path=backend_path,
    )
