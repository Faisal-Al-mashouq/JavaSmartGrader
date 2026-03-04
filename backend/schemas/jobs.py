from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from ocr.ocr_corrector.models import CorrectionResult
from pydantic import BaseModel, Field
from sandbox.schemas import SandboxJobResult


class JobStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ERROR = "ERROR"


class JobType(StrEnum):
    SUBMISSION = "SUBMISSION"
    OCR = "OCR"
    SANDBOX = "SANDBOX"
    GRADER = "GRADER"
    FINAL_RESULT = "FINAL_RESULT"


class TestCase(BaseModel):
    input: Any
    expected_output: Any


class SubmissionPayload(BaseModel):
    type: JobType = Field(default=JobType.SUBMISSION, description="discriminator")
    submission_id: int
    question_id: int
    assignment_id: int
    student_id: int
    image_url: str
    test_cases: list[TestCase]
    rubric_json: dict
    created_at: datetime


class OCRPayload(BaseModel):
    type: JobType = Field(default=JobType.OCR, description="discriminator")
    transcription_id: int
    submission_id: int
    image_url: str
    created_at: datetime


class OCRResult(BaseModel):
    type: JobType = Field(default=JobType.OCR, description="discriminator")
    transcription_id: int
    submission_id: int
    result: CorrectionResult
    created_at: datetime
    finished_at: datetime | None


class SandboxPayload(BaseModel):
    type: JobType = Field(default=JobType.SANDBOX, description="discriminator")
    compilation_id: int
    submission_id: int
    java_code: str
    test_cases: list[TestCase]
    created_at: datetime


class SandboxResult(BaseModel):
    type: JobType = Field(default=JobType.SANDBOX, description="discriminator")
    compilation_id: int
    submission_id: int
    result: SandboxJobResult
    finished_at: datetime | None


class GraderPayload(BaseModel):
    type: JobType = Field(default=JobType.GRADER, description="discriminator")
    feedback_id: int
    submission_id: int
    transcribed_text: str
    sandbox_result: SandboxJobResult
    rubric_json: dict
    created_at: datetime


class GraderResult(BaseModel):
    type: JobType = Field(default=JobType.GRADER, description="discriminator")
    feedback_id: int
    submission_id: int
    rubric_json: dict
    final_grade: float | None = None
    student_feedback: str | None = None
    instructor_guidance: str | None = None
    finished_at: datetime | None = None


class FinalResult(BaseModel):
    type: JobType = Field(default=JobType.FINAL_RESULT, description="discriminator")
    submission_id: int
    result: GraderResult
    finished_at: datetime | None = None


JobPayload = Annotated[
    SubmissionPayload | OCRPayload | SandboxPayload | GraderPayload,
    Field(
        description="The payload of the job",
        discriminator="type",
    ),
]

JobResultPayload = Annotated[
    OCRResult | SandboxResult | GraderResult | FinalResult,
    Field(
        description="The result of the job",
        discriminator="type",
    ),
]


class JobRequest(BaseModel):
    type: JobType
    payload: JobPayload


class JobResult(BaseModel):
    type: JobType
    result: JobResultPayload | None
    finished_at: datetime | None


class Job(BaseModel):
    job_id: UUID
    type: JobType
    status: JobStatus
    request: JobRequest
    result: JobResult | None
