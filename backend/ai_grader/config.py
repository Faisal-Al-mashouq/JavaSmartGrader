from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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
    queue_poll_timeout_s: BRPOPLPUSH blocking timeout in seconds
    temperature: LLM sampling temperature
    pending_review_status: Status applied after successful grading.
    failure_status_candidates: Ordered list of status strings for failures
    backend_path: Filesystem path added to sys.path for DB imports
    log_level: Root logging level for the worker process
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
        populate_by_name=True,
        validate_default=True,
    )

    model: str = Field(default="ft:gpt-4.1-nano-", validation_alias="MODEL")
    api_key: str = Field(default="", validation_alias="API_KEY")
    base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias="BASE_URL",
    )
    timeout_s: float = Field(default=30.0, validation_alias="TIMEOUT_S", ge=1.0)
    max_retries: int = Field(default=3, validation_alias="MAX_RETRIES", ge=0)
    backoff_base_s: float = Field(
        default=1.0,
        validation_alias="BACKOFF_BASE_S",
        ge=0.0,
    )
    backoff_max_s: float = Field(
        default=30.0,
        validation_alias="BACKOFF_MAX_S",
        gt=0.0,
    )
    redis_url: str = Field(
        default="redis://redis:6379",
        validation_alias=AliasChoices("REDIS_ENDPOINT", "REDIS_URL"),
    )
    queue_namespace: str = Field(
        default="jsg.v1",
        validation_alias="QUEUE_NAMESPACE",
        exclude=True,
        repr=False,
    )
    ready_queue_name: str = Field(
        default="Ready_Grading",
        validation_alias="READY_GRADING_QUEUE",
    )
    queue_poll_timeout_s: int = Field(
        default=5,
        validation_alias="QUEUE_POLL_TIMEOUT_S",
        ge=0,
    )
    temperature: float = Field(
        default=0.0,
        validation_alias="LLM_TEMPERATURE",
        ge=0.0,
    )
    pending_review_status: str = Field(
        default="Pending_Review",
        validation_alias="PENDING_REVIEW_STATUS",
    )
    failure_status_candidates: tuple[str, ...] = Field(
        default=("Grading_Failed", "failed"),
        validation_alias="FAILURE_STATUS_CANDIDATES",
    )
    backend_path: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[1],
        validation_alias="BACKEND_PATH",
    )
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    @field_validator("ready_queue_name")
    @classmethod
    def _prefix_ready_queue(cls, value: str, info: ValidationInfo) -> str:
        queue_namespace = str(info.data.get("queue_namespace", "")).strip()
        if not queue_namespace:
            return value
        prefix = f"{queue_namespace}:"
        if value.startswith(prefix):
            return value
        return f"{prefix}{value}"

    @field_validator("failure_status_candidates", mode="before")
    @classmethod
    def _parse_failure_status_candidates(cls, value: Any) -> tuple[str, ...]:
        if isinstance(value, str):
            parsed = tuple(item.strip() for item in value.split(",") if item.strip())
            if not parsed:
                raise ValueError("FAILURE_STATUS_CANDIDATES must not be empty.")
            return parsed
        if isinstance(value, list):
            parsed = tuple(str(item).strip() for item in value if str(item).strip())
            if not parsed:
                raise ValueError("FAILURE_STATUS_CANDIDATES must not be empty.")
            return parsed
        return value


def load_settings() -> Settings:
    """
    Constructs and returns the single Settings instance.
    Called once in main() and passed to all components.
    """
    return Settings()


def configure_logging(settings: Settings) -> None:
    """
    Applies root logging configuration for the ai_grader worker process.
    """
    level_name = settings.log_level.strip().upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        force=True,
    )
