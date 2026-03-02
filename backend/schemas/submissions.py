from datetime import datetime

from db.models import SubmissionState
from pydantic import BaseModel


class SubmissionBase(BaseModel):
    id: int
    question_id: int
    assignment_id: int
    student_id: int
    image_url: str | None
    state: SubmissionState
    submitted_at: datetime

    model_config = {"from_attributes": True}
