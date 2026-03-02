from datetime import datetime

from pydantic import BaseModel


class AssignmentBase(BaseModel):
    id: int
    course_id: int
    title: str
    description: str | None = None
    due_date: datetime | None = None
    rubric_json: dict | None = None

    model_config = {"from_attributes": True}
