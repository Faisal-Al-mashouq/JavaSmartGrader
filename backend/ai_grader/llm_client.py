from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Any

import httpx

from .config import Settings

# provides LLMClient, an async HTTP client that wraps
# the OpenAI-compatible /chat/completions endpoint
# it handles prompt delivery, error classification,
# exponential backoff with jitter, and response text extraction.
# it never blocks the event loop.

logger = logging.getLogger(__name__)


class LLMAPIError(RuntimeError):
    """Base error for unrecoverable LLM API failures"""


class RetryableLLMAPIError(LLMAPIError):
    """Error type for failures that should be retried"""


@dataclass(frozen=True)
class LLMResponse:
    text: str
    attempt_count: int


class LLMClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._url = self._build_chat_completions_url(settings.base_url)

    @staticmethod
    def _build_chat_completions_url(base_url: str) -> str:
        """
        Normalises base_url by stripping trailing slashes and appending
        /chat/completions if needed
        Handles bases that already end in /v1 or /chat/completions
        Returns: str (full endpoint URL)
        """
        normalized = base_url.rstrip("/")
        if normalized.endswith("/chat/completions"):
            return normalized
        if normalized.endswith("/v1"):
            return f"{normalized}/chat/completions"
        return f"{normalized}/chat/completions"

    def _compute_backoff_with_jitter(self, attempt: int) -> float:
        """
        Calculates the sleep duration before the next retry using exponential backoff
        Prevents thundering herd when many workers retry simultaneously.
        Returns: float (seconds to sleep)
        """
        base_delay = min(
            self._settings.backoff_max_s,
            self._settings.backoff_base_s * (2 ** max(0, attempt - 1)),
        )
        jitter = random.uniform(0.0, base_delay * 0.25)
        return min(self._settings.backoff_max_s, base_delay + jitter)

    async def call(self, prompt: str, submission_id: int) -> LLMResponse:
        """
        top-level public method
        loops up to max_retries+1 times
        on RetryableLLMAPIError it sleeps and retries
        on LLMAPIError it re-raises immediately
        On success it returns the LLMResponse
        parameters: prompt: str, submission_id: int (used only for logging)
        returns: LLMResponse
        note: Raises LLMAPIError if api_key is missing or all retries are exhausted.
        """
        if not self._settings.api_key:
            raise LLMAPIError("Missing API_KEY for LLM client")

        total_attempts = max(1, self._settings.max_retries + 1)
        last_error: Exception | None = None

        for attempt in range(1, total_attempts + 1):
            logger.info(
                "LLM call: submission_id=%s attempt=%s/%s",
                submission_id,
                attempt,
                total_attempts,
            )
            try:
                text = await self._call_once(prompt=prompt)
                return LLMResponse(text=text, attempt_count=attempt)
            except RetryableLLMAPIError as exc:
                last_error = exc
                if attempt >= total_attempts:
                    break
                delay = self._compute_backoff_with_jitter(attempt)
                logger.warning(
                    "Retryable LLM error for submission_id=%s attempt=%s/%s: %s. "
                    "Retrying in %.2fs.",
                    submission_id,
                    attempt,
                    total_attempts,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
            except LLMAPIError:
                raise

        raise LLMAPIError(
            f"LLM call failed after {total_attempts} attempts: {last_error}"
        )

    async def _call_once(self, prompt: str) -> str:
        """
        Makes a single HTTP POST to the completions endpoint
        Returns: str (raw content text)
        """
        headers = {
            "Authorization": f"Bearer {self._settings.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._settings.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an expert Java grader. "
                        "Return ONLY valid JSON matching the provided schema. "
                        "No markdown, no extra text."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": self._settings.temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=self._settings.timeout_s) as client:
                response = await client.post(
                    self._url,
                    headers=headers,
                    json=payload,
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise RetryableLLMAPIError(f"Network/timeout error: {exc}") from exc

        if response.status_code == 429 or response.status_code >= 500:
            raise RetryableLLMAPIError(
                f"Retryable HTTP error {response.status_code}: {response.text[:500]}"
            )
        if response.status_code >= 400:
            raise LLMAPIError(
                f"Non-retryable HTTP error {response.status_code}: "
                f"{response.text[:500]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMAPIError("LLM response was not valid JSON") from exc

        text = self._extract_text(data)
        if not text:
            raise LLMAPIError("LLM response missing choices[0].message.content")
        return text

    @staticmethod
    def _extract_text(response_json: dict[str, Any]) -> str | None:
        """
        Safely navigates choices[0].message.content.
        Handles both a plain string content and a list of content blocks
        (extracts all text-type parts and joins them)
        Returns None if the structure is unexpected
        Returns: str | None

        """
        choices = response_json.get("choices")
        if not isinstance(choices, list) or not choices:
            return None
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return None
        message = first_choice.get("message")
        if not isinstance(message, dict):
            return None

        content = message.get("content")
        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            parts: list[str] = []
            for part in content:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    parts.append(part["text"])
            combined = "".join(parts).strip()
            return combined or None

        return None
