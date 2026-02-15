import datetime
import enum
import uuid
from typing import Any

from pydantic import BaseModel


class CompilationRequest(BaseModel):
    java_code: str
    language: str


class TestCasesRequest(BaseModel):
    test_inputs: list[str]
    expected_outputs: list[str]


class SandboxRequest(BaseModel):
    java_code: str
    language: str
    test_inputs: list[str]
    expected_outputs: list[str]


class CompilationResult(BaseModel):
    success: bool
    outputs: list[str]


class TestCaseResult(BaseModel):
    success: bool
    outputs: list[str]
    expected_outputs: list[str]


class SandboxResult(BaseModel):
    compilation_result: CompilationResult
    test_case_results: list[TestCaseResult]
    assertions_results: dict[str, Any]


class JobStatus(enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SandboxJobRequest(BaseModel):
    job_id: uuid.UUID
    status: JobStatus
    created_at: datetime.datetime
    request: SandboxRequest


class SandboxJobResult(BaseModel):
    job_id: uuid.UUID
    status: JobStatus
    result: SandboxResult | None
    error: str | None
