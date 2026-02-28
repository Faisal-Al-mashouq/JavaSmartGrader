from datetime import datetime

from pydantic import BaseModel


class AssignmentBase(BaseModel):
    id: int
    instructor_id: int
    title: str
    question: str
    description: str | None = None
    due_date: datetime | None = None
    suggested_grade: float | None = None
    feedback_text: str | None = None
    rubric_json: dict | None = None

    model_config = {"from_attributes": True}


class TestcaseBase(BaseModel):
    id: int
    assignment_id: int
    input: str
    expected_output: str

    model_config = {"from_attributes": True}
