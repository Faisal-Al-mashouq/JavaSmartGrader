from datetime import datetime

from db.models import SubmissionState
from pydantic import BaseModel

from .confidence_flags import ConfidenceFlagBase


class SubmissionBase(BaseModel):
    id: int
    question_id: int
    assignment_id: int
    student_id: int
    image_url: str | None
    state: SubmissionState
    submitted_at: datetime

    model_config = {"from_attributes": True}


class ApproveTranscriptionRequest(BaseModel):
    approved_text: str


class PendingReviewResponse(BaseModel):
    submission_id: int
    transcription_id: int
    transcribed_text: str | None
    flags: list[ConfidenceFlagBase]
