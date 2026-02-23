import datetime
import enum
import uuid
from typing import Any

from pydantic import BaseModel


class JobStatus(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CompilationJobRequest(BaseModel):
    java_code: str


class CompilationJobResult(BaseModel):
    success: bool
    errors: list[str] | None


class TestCaseRequest(BaseModel):
    input: Any
    expected_output: Any


class TestCasesRequest(BaseModel):
    test_cases: list[TestCaseRequest] | None


class TestCaseResult(BaseModel):
    input: Any
    expected_output: Any
    actual_output: Any
    passed: bool


class TestCasesResult(BaseModel):
    results: list[TestCaseResult] | None


class ExecutionJobRequest(BaseModel):
    compiled_code: str
    test_cases: TestCasesRequest | None


class ExecutionJobResult(BaseModel):
    success: bool
    errors: list[str] | None


class SandboxJobRequest(BaseModel):
    job_id: uuid.UUID
    java_code: str
    test_cases: TestCasesRequest | None


class SandboxResult(BaseModel):
    compilation_result: CompilationJobResult | None
    execution_result: ExecutionJobResult | None
    test_cases_results: TestCasesResult | None


class SandboxJob(BaseModel):
    job_id: uuid.UUID
    status: JobStatus
    created_at: datetime.datetime
    request: (
        SandboxJobRequest
        | CompilationJobRequest
        | ExecutionJobRequest
        | TestCasesRequest
        | None
    )
    result: SandboxResult | None


class SandboxJobResult(BaseModel):
    job_id: uuid.UUID
    status: JobStatus
    result: SandboxResult | None
