from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID

from ocr.ocr_corrector.models import CorrectionResult
from pydantic import BaseModel, Field
from sandbox.schemas import SandboxJobResult


class JobStatus(StrEnum):
    STARTED = "STARTED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ERROR = "ERROR"


class JobType(StrEnum):
    OCR = "OCR"
    SANDBOX = "SANDBOX"
    GRADER = "GRADER"
    FINAL_RESULT = "FINAL_RESULT"


class TestCase(BaseModel):
    input: Any
    expected_output: Any


class OCRPayload(BaseModel):
    type: Literal[JobType.OCR] = Field(default=JobType.OCR, description="discriminator")
    job_id: UUID
    image_url: str


class OCRResult(BaseModel):
    type: Literal[JobType.OCR] = Field(default=JobType.OCR, description="discriminator")
    result: CorrectionResult


class SandboxPayload(BaseModel):
    type: Literal[JobType.SANDBOX] = Field(
        default=JobType.SANDBOX, description="discriminator"
    )
    job_id: UUID
    java_code: str
    test_cases: list[TestCase]


class SandboxResult(BaseModel):
    type: Literal[JobType.SANDBOX] = Field(
        default=JobType.SANDBOX, description="discriminator"
    )
    result: SandboxJobResult


class GraderPayload(BaseModel):
    type: Literal[JobType.GRADER] = Field(
        default=JobType.GRADER, description="discriminator"
    )
    job_id: UUID
    transcribed_text: str
    sandbox_result: SandboxJobResult
    rubric_json: dict


class GraderResult(BaseModel):
    type: Literal[JobType.GRADER] = Field(
        default=JobType.GRADER, description="discriminator"
    )
    rubric_result_json: dict
    final_grade: float | None = None
    student_feedback: str | None = None
    instructor_guidance: str | None = None


class FinalResult(BaseModel):
    type: Literal[JobType.FINAL_RESULT] = Field(
        default=JobType.FINAL_RESULT, description="discriminator"
    )
    job_id: UUID
    result: GraderResult | None = None


JobPayloadUnion = Annotated[
    OCRPayload | SandboxPayload | GraderPayload,
    Field(
        description="The payload of the job",
        discriminator="type",
    ),
]


JobResultUnion = Annotated[
    OCRResult | SandboxResult | GraderResult | FinalResult,
    Field(
        description="The result of the job",
        discriminator="type",
    ),
]


class JobRequest(BaseModel):
    submission_id: int
    question_id: int
    assignment_id: int
    student_id: int
    image_url: str
    java_code: str
    test_cases: list[TestCase]
    rubric_json: dict


class JobRequestPayload(BaseModel):
    job_payload: JobPayloadUnion
    created_at: datetime


class JobResultPayload(BaseModel):
    job_result: JobResultUnion | None = None
    finished_at: datetime | None = None


class Job(BaseModel):
    job_id: UUID
    status: JobStatus
    initial_request: JobRequest
    job_request_payload: list[JobRequestPayload] = Field(default_factory=list)
    job_result_payload: list[JobResultPayload] = Field(default_factory=list)
    created_at: datetime
    finished_at: datetime | None = None
