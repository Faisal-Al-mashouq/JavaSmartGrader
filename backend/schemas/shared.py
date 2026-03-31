"""
Shared types used across multiple modules (API schemas, sandbox, OCR workers).

Centralised here to avoid duplication and ensure consistent serialisation
(StrEnum → JSON-safe string values everywhere).
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class JobStatus(StrEnum):
    STARTED = "STARTED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ERROR = "ERROR"


class TestCase(BaseModel):
    input: Any
    expected_output: Any
