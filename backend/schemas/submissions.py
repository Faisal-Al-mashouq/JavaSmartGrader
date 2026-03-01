from datetime import datetime

from pydantic import BaseModel

from db.models import SubmissionState


class SubmissionBase(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    image_url: str | None
    state: SubmissionState
    submitted_at: datetime

    model_config = {"from_attributes": True}
